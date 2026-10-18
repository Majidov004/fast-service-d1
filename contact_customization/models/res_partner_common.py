# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartnerCommon(models.Model):
    """Shared fields used by both Applicants and Students."""
    _inherit = 'res.partner'

    # ── Identity flags ────────────────────────────────────────────────────────

    is_student = fields.Boolean(string='Student', default=False)
    is_applicant = fields.Boolean(string='Applicant', default=False)

    # ── Shared profile fields ─────────────────────────────────────────────────

    manager_id = fields.Many2one(
        'hr.employee',
        string='Registrar',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if not res.get('manager_id'):
            employee = self.env.user.employee_id
            if employee:
                res['manager_id'] = employee.id
        return res
    teacher_id = fields.Many2one(
        'hr.employee',
        string='Teacher',
        help='Teacher assigned for the trial lesson',
    )
    expected_join_date = fields.Date(
        string='Expected Join Date',
        tracking=True,
        help='Auto-filled from trial lesson Join Timing.',
    )
    current_level = fields.Selection([
        ('a1', 'A1 - Beginner'),
        ('a2', 'A2 - Elementary'),
        ('b1', 'B1 - Pre-Intermediate'),
        ('b2', 'B2 - Intermediate'),
        ('c1', 'C1 - Advanced'),
        ('c2', 'C2 - Proficiency'),
    ], string='Current Level')

    reference_source = fields.Selection([
        ('tiktok_organic',    'TikTok (Found us)'),
        ('tiktok_ads',        'TikTok (Ad)'),
        ('instagram_organic', 'Instagram (Found us)'),
        ('instagram_ads',     'Instagram (Ad)'),
        ('facebook_organic',  'Facebook (Found us)'),
        ('facebook_ads',      'Facebook (Ad)'),
        ('whatsapp',          'WhatsApp'),
        ('linkedin_organic',  'LinkedIn (Found us)'),
        ('linkedin_ads',      'LinkedIn (Ad)'),
        ('youtube_organic',   'YouTube (Found us)'),
        ('youtube_ads',       'YouTube (Ad)'),
        ('acquaintance',      'Acquaintance'),
        ('mail',              'Mail'),
    ], string='Reference')

    # ── Platform account names ────────────────────────────────────────────────

    reference_tiktok_account    = fields.Char(string='TikTok Account Name')
    reference_instagram_account = fields.Char(string='Instagram Account Name')
    reference_facebook_account  = fields.Char(string='Facebook Account Name')
    reference_whatsapp_account  = fields.Char(string='WhatsApp Number')
    reference_linkedin_account  = fields.Char(string='LinkedIn Profile URL')
    reference_youtube_account   = fields.Char(string='YouTube Channel Name')

    # ── Trial lesson smart button ─────────────────────────────────────────────

    trail_lesson_count = fields.Integer(
        string='Trial Lessons',
        compute='_compute_trail_lesson_count',
    )

    def action_view_trail_lessons(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Trial Lessons',
            'res_model': 'trail.lesson',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id)],
            'context': {'default_student_id': self.id},
        }

    @api.depends()
    def _compute_trail_lesson_count(self):
        for rec in self:
            rec.trail_lesson_count = self.env['trail.lesson'].search_count(
                [('student_id', '=', rec.id)]
            )

    # ── Active trial lesson (most recent) ────────────────────────────────────

    trial_lesson_id = fields.Many2one(
        'trail.lesson',
        string='Trial Lesson',
        compute='_compute_trial_lesson_id',
        store=False,
    )

    @api.depends()
    def _compute_trial_lesson_id(self):
        TrailLesson = self.env['trail.lesson']
        for rec in self:
            rec.trial_lesson_id = TrailLesson.search(
                [('student_id', '=', rec.id)],
                order='lesson_datetime desc',
                limit=1,
            )

    # ── Trial Detail: related display fields (readonly) ───────────────────────

    tl_gender = fields.Selection(
        related='trial_lesson_id.gender', string='Gender', readonly=True)
    tl_approximate_age = fields.Selection(
        related='trial_lesson_id.approximate_age', string='Approx. Age Group', readonly=True)

    # ── Config Many2one related fields ────────────────────────────────────────
    tl_company_id = fields.Many2one(
        'trail.lesson.config.company',
        related='trial_lesson_id.lesson_company_id',
        string='Company',
        readonly=True,
    )
    tl_position_id = fields.Many2one(
        'trail.lesson.config.position',
        related='trial_lesson_id.position_id',
        string='Position / Title',
        readonly=True,
    )
    tl_school_id = fields.Many2one(
        'trail.lesson.config.school',
        related='trial_lesson_id.school_id',
        string='School',
        readonly=True,
    )
    tl_learning_purpose_id = fields.Many2one(
        'trail.lesson.config.learning.purpose',
        related='trial_lesson_id.learning_purpose_id',
        string='Learning Purpose',
        readonly=True,
    )
    tl_course_id = fields.Many2one(
        'trail.lesson.config.course',
        related='trial_lesson_id.course_id',
        string='Previous Course',
        readonly=True,
    )
    # ── End config Many2one related fields ────────────────────────────────────

    tl_english_level = fields.Selection(
        related='trial_lesson_id.english_level', string='English Level', readonly=True)
    tl_for_whom = fields.Selection(
        related='trial_lesson_id.for_whom', string='For Whom', readonly=True)
    tl_for_whom_note = fields.Char(
        related='trial_lesson_id.for_whom_note', string='For Whom (detail)', readonly=True)

    tl_comprehension = fields.Selection(
        related='trial_lesson_id.comprehension', string='Comprehension', readonly=True)
    tl_motivation = fields.Selection(
        related='trial_lesson_id.motivation', string='Motivation', readonly=True)
    tl_previous_courses = fields.Boolean(
        related='trial_lesson_id.previous_courses', string='Previous Courses', readonly=True)

    tl_decision = fields.Selection(
        related='trial_lesson_id.decision', string='Decision', readonly=True)
    tl_thinking_reason = fields.Selection(
        related='trial_lesson_id.thinking_reason', string='Reason for Thinking', readonly=True)
    tl_system_choice = fields.Selection(
        related='trial_lesson_id.system_choice', string='System Choice', readonly=True)
    tl_system_choice_note = fields.Char(
        related='trial_lesson_id.system_choice_note', string='System Choice Note', readonly=True)
    tl_lesson_format = fields.Selection(
        related='trial_lesson_id.lesson_format', string='Preferred Format', readonly=True)
    tl_payment_type = fields.Selection(
        related='trial_lesson_id.payment_type', string='Payment Type', readonly=True)
    tl_payment_amount = fields.Float(
        related='trial_lesson_id.payment_amount', string='Payment Amount', readonly=True)
    tl_join_timing = fields.Selection(
        related='trial_lesson_id.join_timing', string='Join Timing', readonly=False)
    tl_expected_join_date = fields.Date(
        related='trial_lesson_id.expected_join_date', string='Expected Join Date', readonly=True)

    # ✅ FIX: Status 'remember' + join_timing doldurulduqda expected_join_date sinxronlaşır
    @api.onchange('tl_join_timing')
    def _onchange_tl_join_timing_remember(self):
        if self.applicant_state == 'remember' and self.tl_join_timing:
            self.expected_join_date = self.tl_expected_join_date

    tl_complete_notes = fields.Text(
        related='trial_lesson_id.complete_notes',
        string='Completion Notes',
        readonly=True,
    )

    # Q&A — computed Many2many since trail.lesson.qa has no direct partner FK
    tl_qa_ids = fields.Many2many(
        'trail.lesson.qa',
        string='Q&A Session',
        compute='_compute_tl_qa_ids',
    )

    @api.depends('trial_lesson_id')
    def _compute_tl_qa_ids(self):
        for rec in self:
            rec.tl_qa_ids = (
                rec.trial_lesson_id.qa_ids
                if rec.trial_lesson_id
                else self.env['trail.lesson.qa']
            )

    # ── Training Group smart button ───────────────────────────────────────────

    training_group_count = fields.Integer(
        string='Training Groups',
        compute='_compute_training_group_count',
    )

    @api.depends()
    def _compute_training_group_count(self):
        Group = self.env['training.group']
        for rec in self:
            rec.training_group_count = Group.search_count(
                [('student_line_ids.student_id', '=', rec.id)]
            )

    def action_view_training_groups(self):
        """Open the training groups the student is enrolled in."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Training Groups',
            'res_model': 'training.group',
            'view_mode': 'list,form',
            'domain': [('student_line_ids.student_id', '=', self.id)],
        }

    # ── Meeting tab: per-student lesson comments ──────────────────────────────

    # Attach point for the meeting_comments_widget (data loaded via get_meeting_comments)
    meeting_line_ids = fields.One2many(
        'lesson.student.line',
        'student_id',
        string='Meeting Comments',
    )

    def get_meeting_comments(self):
        """Return this student's lesson comments grouped by training group.

        Only lesson lines that have a comment for this student are included.
        Used by the OWL meeting_comments_widget.
        """
        self.ensure_one()
        lines = self.env['lesson.student.line'].search([
            ('student_id', '=', self.id),
            ('comment', '!=', False),
            ('comment', '!=', ''),
        ])
        groups = {}
        order = []
        for line in lines:
            lesson = line.lesson_id
            group = lesson.group_id
            gid = group.id or 0
            if gid not in groups:
                groups[gid] = {
                    'group_id': group.id or False,
                    'group_name': group.name or 'No Group',
                    'teacher_name': group.teacher_id.name if group.teacher_id else '',
                    'lessons': [],
                }
                order.append(gid)
            d = lesson.lesson_date
            groups[gid]['lessons'].append({
                'id': line.id,
                'lesson_name': lesson.name or '',
                'lesson_number': lesson.lesson_number,
                'date': d.strftime('%d-%m-%Y') if d else '',
                'date_sort': str(d) if d else '',
                'attendance': line.attendance or '',
                'comment': line.comment or '',
            })
        for gid in groups:
            groups[gid]['lessons'].sort(key=lambda x: x['date_sort'], reverse=True)
        return [groups[gid] for gid in order]