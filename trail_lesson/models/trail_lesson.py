# -*- coding: utf-8 -*-
import pytz
from pytz import timezone
from markupsafe import Markup
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from .trail_lesson_question import SYSTEM_SELECTION, LEVEL_SELECTION


class TrailLessonQA(models.Model):
    """Persistent Q&A lines linked to a completed trail lesson."""
    _name = 'trail.lesson.qa'
    _description = 'Trail Lesson Q&A'
    _order = 'sequence, id'

    lesson_id = fields.Many2one(
        comodel_name='trail.lesson',
        string='Lesson',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(string='#', default=10)
    question = fields.Char(string='Question (EN)', required=True)
    answer = fields.Char(string="Student's Answer")
    translation = fields.Char(string='Translation (AZ/RU)')


class TrailLesson(models.Model):
    _name = 'trail.lesson'
    _description = 'Trail Lesson'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'lesson_datetime desc'

    # ── Core Fields ───────────────────────────────────────────────────────────

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    state = fields.Selection(
        selection=[
            ('not_planned', 'Not Planned'),
            ('planned', 'Planned'),
            ('completed', 'Completed'),
            ('missing', 'Missing Lesson'),
        ],
        string='Status',
        default='not_planned',
        required=True,
        tracking=True,
        copy=False,
    )
    teacher_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Teacher',
        required=True,
        tracking=True,
    )
    student_id = fields.Many2one(
        comodel_name='res.partner',
        string='Student',
        required=True,
        tracking=True,
    )
    lesson_datetime = fields.Datetime(
        string='Lesson Date & Time',
        required=True,
        tracking=True,
    )
    video_record = fields.Binary(
        string='Video Record',
        attachment=True,
    )
    video_record_filename = fields.Char(string='Video Filename')
    video_preview_html = fields.Html(
        string='Video Preview',
        compute='_compute_video_preview_html',
        sanitize=False,
    )
    notes = fields.Html(string='Notes')
    complete_notes = fields.Text(string='Completion Notes')

    # ── Assessment – Student Background ───────────────────────────────────────

    lesson_company_id = fields.Many2one(
        comodel_name='trail.lesson.config.company',
        string='Company',
    )
    position_id = fields.Many2one(
        comodel_name='trail.lesson.config.position',
        string='Position / Title',
    )
    school_id = fields.Many2one(
        comodel_name='trail.lesson.config.school',
        string='School / Uni',
    )
    gender = fields.Selection(
        selection=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
        string='Gender',
    )
    approximate_age = fields.Selection(
        selection=[
            ('under_18', 'Under 18'),
            ('18_25', '18–25'),
            ('26_35', '26–35'),
            ('36_45', '36–45'),
            ('46_55', '46–55'),
            ('over_55', 'Over 55'),
        ],
        string='Approx. Age Group',
    )
    english_level = fields.Selection(
        selection=[
            ('a1', 'A1 – Beginner'),
            ('a2', 'A2 – Elementary'),
            ('b1', 'B1 – Pre-Intermediate'),
            ('b2', 'B2 – Intermediate'),
            ('c1', 'C1 – Advanced'),
            ('c2', 'C2 – Proficiency'),
        ],
        string='English Level',
        tracking=True,
    )

    # ── Assessment – Q&A ─────────────────────────────────────────────────────

    qa_ids = fields.One2many(
        comodel_name='trail.lesson.qa',
        inverse_name='lesson_id',
        string='Questions & Answers',
    )

    # ── Assessment – Evaluation ───────────────────────────────────────────────

    comprehension = fields.Selection(
        selection=[
            ('poor', 'Poor'),
            ('average', 'Average'),
            ('good', 'Good'),
            ('excellent', 'Excellent'),
        ],
        string='Comprehension Ability',
    )
    motivation = fields.Selection(
        selection=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')],
        string='Motivation / Enthusiasm',
    )
    learning_purpose_id = fields.Many2one(
        comodel_name='trail.lesson.config.learning.purpose',
        string='Learning Purpose',
    )
    previous_courses = fields.Boolean(string='Attended Other Courses Before')
    course_id = fields.Many2one(
        comodel_name='trail.lesson.config.course',
        string='Previous Course',
        help='Course the student attended before.',
    )
    for_whom = fields.Selection(
        selection=[
            ('self', 'Themselves'),
            ('child', 'Child'),
            ('spouse', 'Spouse / Partner'),
            ('other', 'Other'),
        ],
        string='For Whom',
        default='self',
    )
    for_whom_note = fields.Char(string='For Whom (detail)')

    # ── Assessment – Decision ─────────────────────────────────────────────────

    decision = fields.Selection(
        selection=[
            ('joining', 'Will Join'),
            ('not_joining', 'Will Not Join'),
            ('thinking', 'Still Thinking'),
        ],
        string='Student Decision',
        tracking=True,
    )
    thinking_reason = fields.Selection(
        selection=[
            ('price', 'Price Concern'),
            ('schedule', 'Schedule Conflict'),
            ('family', 'Needs to Consult Family'),
            ('comparing', 'Comparing with Other Schools'),
            ('other', 'Other'),
        ],
        string='Reason for Thinking',
    )
    system_choice = fields.Selection(
        selection=SYSTEM_SELECTION,
        string='System Choice',
    )
    system_choice_note = fields.Char(string='System Choice Note')
    lesson_format = fields.Selection(
        selection=[('group', 'Group'), ('individual', 'Individual')],
        string='Preferred Format',
    )
    payment_type = fields.Selection(
        selection=[
            ('full', 'Full Payment'),
            ('deposit', 'Deposit / Reservation'),
        ],
        string='Payment Type',
    )
    payment_amount = fields.Float(
        string='Payment Amount',
        digits=(10, 2),
    )
    join_timing = fields.Selection(
        selection=[
            ('now', 'Now'),
            ('1_week', 'Within 1 Week'),
            ('2_weeks', 'Within 2 Weeks'),
            ('1_month', 'Within 1 Month'),
            ('3_months', 'Within 3 Months'),
            ('later', 'Later / Unknown'),
        ],
        string='Join Timing',
    )
    expected_join_date = fields.Date(
        string='Expected Join Date',
        tracking=True,
    )

    # ── Computed ──────────────────────────────────────────────────────────────

    @api.depends('video_record', 'video_record_filename')
    def _compute_video_preview_html(self):
        for rec in self:
            if rec.video_record and rec.id:
                filename = rec.video_record_filename or 'video'
                url = (
                    '/web/content?model=trail.lesson'
                    '&id=%d'
                    '&field=video_record'
                    '&filename=%s'
                ) % (rec.id, filename)
                rec.video_preview_html = (
                    '<div style="text-align:center;padding:16px;">'
                    '<video controls style="width:100%%;max-height:480px;'
                    'border-radius:8px;background:#000;">'
                    '<source src="%s">'
                    '<p>Your browser does not support the video tag.</p>'
                    '</video></div>'
                ) % url
            else:
                rec.video_preview_html = (
                    '<p style="color:#888;padding:24px;text-align:center;">'
                    '&#9654; No video uploaded yet. Please upload a video record above.'
                    '</p>'
                )

    # ── ORM Overrides ─────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('trail.lesson') or _('New')
                )
        records = super(TrailLesson, self.with_context(mail_create_nolog=True)).create(vals_list)
        for rec in records:
            partner = rec.student_id
            if partner and partner.is_applicant and partner.applicant_state not in (
                'paid', 'not_want', 'planned_trial', 'planned_remember',
            ):
                partner.applicant_state = 'planned_trial'
        return records

    _STATE_LABELS = {
        'not_planned': 'Not Planned',
        'planned':     'Planned',
        'completed':   'Completed',
        'missing':     'Missing Lesson',
    }

    def write(self, vals):
        old_states = {}
        if 'state' in vals:
            old_states = {rec.id: rec.state for rec in self}
        res = super().write(vals)
        if 'state' in vals:
            new_state = vals['state']
            for rec in self:
                if old_states.get(rec.id) == new_state:
                    continue
                if new_state == 'missing':
                    continue  # action_missing() already posts to partner chatter
                partner = rec.student_id
                if partner and (partner.is_applicant or partner.is_student):
                    old_label = self._STATE_LABELS.get(old_states.get(rec.id), '')
                    new_label = self._STATE_LABELS.get(new_state, new_state)
                    partner.message_post(
                        body=Markup(
                            'Trial Lesson <b><a href="/web#id=%d&amp;model=trail.lesson'
                            '&amp;view_type=form">%s</a></b>: %s → <b>%s</b>'
                        ) % (rec.id, rec.name, old_label, new_label),
                        subtype_xmlid='mail.mt_note',
                    )
        return res

    # ── Button Actions ────────────────────────────────────────────────────────

    def action_schedule(self):
        """Move record to Planned state and create a reminder Activity."""
        for rec in self:
            if rec.state != 'not_planned':
                raise UserError(_('Only lessons in "Not Planned" state can be scheduled.'))
            if not rec.lesson_datetime:
                raise UserError(_('Please set the Lesson Date & Time before scheduling.'))

            rec.state = 'planned'

            user_tz = self.env.user.tz or 'UTC'
            local_tz = timezone(user_tz)
            lesson_local = pytz.utc.localize(rec.lesson_datetime).astimezone(local_tz)
            lesson_str = lesson_local.strftime('%d-%m-%Y %H:%M')

            self.env['mail.activity'].sudo().create({
                'res_model_id': self.env['ir.model']._get('trail.lesson').id,
                'res_id': rec.id,
                'activity_type_id': self.env.ref('mail.mail_activity_data_meeting').id,
                'summary': f"Trial Lesson: {rec.student_id.name} / {rec.teacher_id.name}",
                'date_deadline': rec.lesson_datetime.date(),
                'user_id': (
                    rec.teacher_id.user_id.id if rec.teacher_id.user_id else self.env.uid
                ),
                'note': (
                    f"Teacher: {rec.teacher_id.name}<br/>"
                    f"Student: {rec.student_id.name}<br/>"
                    f"Date: {lesson_str}"
                ),
            })

        return True

    def action_complete(self):
        """Open the Complete Lesson wizard."""
        self.ensure_one()
        if self.state != 'planned':
            raise UserError(_('Only planned lessons can be marked as completed.'))

        return {
            'name': _('Complete Trial Lesson'),
            'type': 'ir.actions.act_window',
            'res_model': 'trail.lesson.complete.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_lesson_id': self.id},
        }

    def action_missing(self):
        """Mark the lesson as Missing (not conducted) — no wizard, instant transition."""
        for rec in self:
            if rec.state != 'planned':
                raise UserError(_('Only planned lessons can be marked as missing.'))

            activities = self.env['mail.activity'].search([
                ('res_model', '=', 'trail.lesson'),
                ('res_id', '=', rec.id),
            ])
            activities.action_done()

            rec.state = 'missing'

            partner = rec.student_id
            if partner and partner.is_applicant:
                partner.applicant_state = 'no_answer'
                partner.no_answer_type = 'before_trial'
                partner.message_post(
                    body=Markup(
                        'Trial Lesson <b><a href="/web#id=%d&amp;model=trail.lesson'
                        '&amp;view_type=form">%s</a></b>: Planned → <b>Missing Lesson</b>'
                    ) % (rec.id, rec.name),
                    subtype_xmlid='mail.mt_note',
                )

            rec.message_post(
                body=Markup('<b>Lesson marked as Missing.</b> The lesson was not conducted.'),
                subtype_xmlid='mail.mt_note',
            )
        return True

    def action_modify(self):
        """Mark existing activities done and recreate the reminder activity."""
        self.ensure_one()
        if self.state != 'planned':
            raise UserError(_('Only planned lessons can be modified.'))
        if not self.lesson_datetime:
            raise UserError(_('Please set the Lesson Date & Time before modifying.'))

        # Close old activities
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'trail.lesson'),
            ('res_id', '=', self.id),
        ])
        activities.action_done()

        # Recreate activity
        user_tz = self.env.user.tz or 'UTC'
        local_tz = timezone(user_tz)
        lesson_local = pytz.utc.localize(self.lesson_datetime).astimezone(local_tz)
        lesson_str = lesson_local.strftime('%d-%m-%Y %H:%M')

        self.env['mail.activity'].sudo().create({
            'res_model_id': self.env['ir.model']._get('trail.lesson').id,
            'res_id': self.id,
            'activity_type_id': self.env.ref('mail.mail_activity_data_meeting').id,
            'summary': f"Trial Lesson: {self.student_id.name} / {self.teacher_id.name}",
            'date_deadline': self.lesson_datetime.date(),
            'user_id': (
                self.teacher_id.user_id.id if self.teacher_id.user_id else self.env.uid
            ),
            'note': (
                f"Teacher: {self.teacher_id.name}<br/>"
                f"Student: {self.student_id.name}<br/>"
                f"Date: {lesson_str}"
            ),
        })
        return True

    def action_plan_new_trial(self):
        """Open the Plan New Trial wizard, pre-filling the current student."""
        self.ensure_one()
        return {
            'name': _('Plan New Trial Lesson'),
            'type': 'ir.actions.act_window',
            'res_model': 'trail.lesson.plan.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
            'default_student_id': self.student_id.id,
            'default_teacher_id': self.teacher_id.id,
        },
        }