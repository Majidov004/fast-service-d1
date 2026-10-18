import logging

from markupsafe import Markup
from odoo import _, models, fields, api

_logger = logging.getLogger(__name__)


class TrainingExam(models.Model):
    _name = 'training.exam'
    _description = 'Training Exam'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'group_id, exam_number'

    name = fields.Char(string='Exam', readonly=True, copy=False, default='New')
    group_id = fields.Many2one(
        'training.group', string='Training Group',
        required=True, ondelete='cascade'
    )
    exam_number = fields.Integer(string='Exam Number', readonly=True, default=0)
    after_lesson_number = fields.Integer(string='After Lesson', readonly=True, default=0)

    teacher_id = fields.Many2one(
        'hr.employee', string='Teacher',
        related='group_id.teacher_id', store=True, readonly=True
    )
    exam_teacher_id = fields.Many2one(
        'hr.employee', string='Exam Teacher',
        related='group_id.exam_teacher_id', store=True, readonly=True
    )
    state = fields.Selection([
        ('waiting', 'Waiting'),
        ('ready', 'Exam Time'),
        ('done', 'Completed'),
    ], string='Status', default='waiting', required=True, tracking=True)

    student_line_ids = fields.One2many(
        'training.exam.student.line', 'exam_id', string='Students'
    )
    student_count = fields.Integer(compute='_compute_counts', store=True)
    weak_count = fields.Integer(compute='_compute_counts', store=True)

    @api.depends('student_line_ids', 'student_line_ids.result')
    def _compute_counts(self):
        for rec in self:
            rec.student_count = len(rec.student_line_ids)
            rec.weak_count = len(
                rec.student_line_ids.filtered(lambda l: l.result == 'zeif')
            )

    # ── Notification helpers ─────────────────────────────────────────────────

    def _partner_of_employee(self, employee):
        """Resolve an hr.employee to a res.partner for messaging."""
        if not employee:
            return self.env['res.partner']
        return employee.user_id.partner_id if employee.user_id else employee.address_id

    def _mention(self, partner):
        return Markup(
            f'<a href="/web#model=res.partner&amp;id={partner.id}" '
            f'data-oe-model="res.partner" data-oe-id="{partner.id}" '
            f'class="o_mail_redirect">@{partner.name}</a>'
        )

    def _post_notification(self, partners, body):
        """Post to the Administrators channel (→ push) + this exam's chatter."""
        self.ensure_one()
        partners = partners.filtered(lambda p: p)
        if not partners:
            return
        admin_partner = self.env.ref('base.user_admin').partner_id
        channel = self.env.ref('mail.channel_admin').sudo()
        channel.message_post(
            body=body,
            author_id=admin_partner.id,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
            partner_ids=partners.ids,
        )
        self.sudo().message_post(
            body=body,
            author_id=admin_partner.id,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )

    # ── State transitions + notifications ────────────────────────────────────

    def action_set_ready(self):
        """Block finished → it's exam time. Notify the exam teacher."""
        for exam in self:
            if exam.state != 'waiting':
                continue
            exam.state = 'ready'
            exam._notify_exam_ready()

    def _notify_exam_ready(self):
        self.ensure_one()
        partner = self._partner_of_employee(self.exam_teacher_id)
        if not partner:
            _logger.warning(
                "EXAM NOTIFY SKIP: no exam teacher partner — exam id=%s", self.id
            )
            return

        body = Markup(
            f'📝 {self._mention(partner)} <b>{self.name}</b> — qrupun '
            f'{self.after_lesson_number}-ci dərsi bitdi, imtahan vaxtıdır.'
        )
        self._post_notification(partner, body)

        # A concrete "request" for the exam teacher (To-Do activity)
        if self.exam_teacher_id.user_id:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('Conduct exam: %s') % self.name,
                user_id=self.exam_teacher_id.user_id.id,
            )
        _logger.info("EXAM READY: %s → exam teacher %s", self.name, partner.name)

    def _mark_done_and_notify(self):
        """Results entered → mark done and notify the teacher about weak students."""
        self.ensure_one()
        first_completion = self.state != 'done'
        self.state = 'done'

        if not first_completion:
            return

        weak_lines = self.student_line_ids.filtered(lambda l: l.result == 'zeif')
        if not weak_lines:
            return

        recipients = self._partner_of_employee(self.teacher_id)
        if not recipients:
            _logger.warning(
                "EXAM WEAK NOTIFY SKIP: no teacher partner — exam id=%s",
                self.id,
            )
            return

        names = ', '.join(weak_lines.mapped('student_id.name'))
        mentions = Markup(' ').join(self._mention(p) for p in recipients)
        body = Markup(
            f'⚠️ {mentions} <b>{self.name}</b> imtahanında zəif nəticə '
            f'göstərən tələbə(lər): <b>{names}</b>.'
        )
        self._post_notification(recipients, body)
        _logger.info("EXAM WEAK: %s → %s", self.name, names)


    # ── Question Bank sync ───────────────────────────────────────────────────

    def _sync_questions(self):
        """Pull the matching Question Bank rows into every student line.

        Questions are selected by exam number + the group's program, so a
        different program gives a different question set for the same exam.
        Existing answer rows are kept (only missing questions are added), and a
        completed exam is left untouched.
        """
        self.ensure_one()
        if self.state == 'done':
            return
        questions = self.env['trail.lesson.question'].fetch_questions(
            'exam',
            exam_number=self.exam_number,
            system=self.group_id.system_choice,
        )
        if not questions:
            return
        Answer = self.env['training.exam.answer']
        for line in self.student_line_ids:
            known = line.answer_ids.mapped('question_id').ids
            for index, question in enumerate(questions, start=1):
                if question.id in known:
                    continue
                Answer.create({
                    'line_id':     line.id,
                    'question_id': question.id,
                    'question':    question._display_question(),
                    'sequence':    index * 10,
                })


class TrainingExamStudentLine(models.Model):

    _name = 'training.exam.student.line'
    _description = 'Training Exam Student Line'
    _rec_name = 'student_id'

    exam_id = fields.Many2one(
        'training.exam', string='Exam',
        required=True, ondelete='cascade'
    )
    student_id = fields.Many2one('res.partner', string='Student', required=True)
    result = fields.Selection([
        ('zeif', 'Weak'),
        ('orta', 'Average'),
        ('ela', 'Excellent'),
    ], string='Result')
    note = fields.Text(string='Notes')
    answer_ids = fields.One2many(
        'training.exam.answer', 'line_id', string='Answers'
    )

    _sql_constraints = [
        ('uniq_exam_student', 'UNIQUE(exam_id, student_id)',
         'A student cannot appear twice in the same exam!'),
    ]


class TrainingExamAnswer(models.Model):
    """One question + this student's answer inside an exam.

    Rows are generated from the shared Question Bank (`trail.lesson.question`,
    stage = Exam) the first time the exam popup is opened.
    """
    _name = 'training.exam.answer'
    _description = 'Training Exam Answer'
    _order = 'sequence, id'

    line_id = fields.Many2one(
        'training.exam.student.line', string='Exam Student Line',
        required=True, ondelete='cascade', index=True
    )
    question_id = fields.Many2one(
        'trail.lesson.question', string='Question (bank)', ondelete='set null'
    )
    question = fields.Text(string='Question', required=True)
    answer = fields.Char(string="Student's Answer")
    sequence = fields.Integer(string='#', default=10)

    _sql_constraints = [
        ('uniq_line_question', 'UNIQUE(line_id, question_id)',
         'A question cannot be asked twice to the same student in one exam!'),
    ]
