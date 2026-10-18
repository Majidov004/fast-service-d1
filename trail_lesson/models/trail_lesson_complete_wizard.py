# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date, timedelta

from .trail_lesson_question import SYSTEM_SELECTION, LEVEL_SELECTION


class TrailLessonCompleteWizardQA(models.TransientModel):
    """Transient Q&A lines used only inside the Complete Lesson wizard."""
    _name = 'trail.lesson.complete.wizard.qa'
    _description = 'Complete Lesson Wizard – Q&A Line'
    _order = 'sequence, id'

    wizard_id = fields.Many2one(
        comodel_name='trail.lesson.complete.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(string='#', default=10)
    question_id = fields.Many2one(
        comodel_name='trail.lesson.question',
        string='From Bank',
        help='The question-bank entry this line was loaded from (if any).',
    )
    question = fields.Char(string='Question (EN)', required=True)
    answer = fields.Char(string="Student's Answer")
    translation = fields.Char(string='Translation (AZ/RU)')


class TrailLessonCompleteWizard(models.TransientModel):
    """Wizard shown when a teacher clicks 'Complete Trial'.
    Collects student assessment data and writes it back to the lesson.
    """
    _name = 'trail.lesson.complete.wizard'
    _description = 'Complete Trial Lesson Wizard'

    lesson_id = fields.Many2one(
        comodel_name='trail.lesson',
        string='Lesson',
        required=True,
        readonly=True,
    )

    # ── Student Background ────────────────────────────────────────────────────

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
        selection=LEVEL_SELECTION,
        string='English Level',
    )

    # ── Q&A Session ───────────────────────────────────────────────────────────

    qa_level = fields.Selection(
        selection=LEVEL_SELECTION,
        string='Question Level',
        help='Pick a level to pull the matching questions from the Question Bank.',
    )
    qa_ids = fields.One2many(
        comodel_name='trail.lesson.complete.wizard.qa',
        inverse_name='wizard_id',
        string='Questions & Answers',
    )

    def _load_bank_questions(self):
        """Refill the Q&A lines from the Question Bank for the chosen level.

        Lines already typed are replaced -- changing the level means starting the
        question set over. Questions stay fully editable afterwards.
        """
        self.ensure_one()
        questions = self.env['trail.lesson.question'].fetch_questions(
            'trial', level=self.qa_level, system=self.system_choice,
        )
        lines = [(5, 0, 0)]
        for seq, question in enumerate(questions, start=1):
            lines.append((0, 0, {
                'sequence':    seq * 10,
                'question_id': question.id,
                'question':    question._display_question(),
                'translation': question.translation,
            }))
        self.qa_ids = lines

    @api.onchange('qa_level')
    def _onchange_qa_level(self):
        if self.qa_level:
            self._load_bank_questions()

    @api.onchange('english_level')
    def _onchange_english_level_qa(self):
        """Default the question level to the assessed English level."""
        if self.english_level and not self.qa_level:
            self.qa_level = self.english_level
            self._load_bank_questions()

    def action_load_questions(self):
        """Manual reload button on the Q&A tab (keeps the wizard open)."""
        self.ensure_one()
        self._load_bank_questions()
        return {
            'type':      'ir.actions.act_window',
            'res_model': self._name,
            'res_id':    self.id,
            'view_mode': 'form',
            'target':    'new',
            'context':   self.env.context,
        }

    # ── Evaluation ────────────────────────────────────────────────────────────

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

    # ── Decision ─────────────────────────────────────────────────────────────

    decision = fields.Selection(
        selection=[
            ('joining', 'Will Join'),
            ('not_joining', 'Will Not Join'),
            ('thinking', 'Still Thinking'),
        ],
        string='Student Decision',
        required=True,
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
        required=True,
    )
    expected_join_date = fields.Date(
        string='Expected Join Date',
        help='Auto-filled from Join Timing; can be edited manually.',
    )
    wizard_notes = fields.Text(string='Additional Notes')

    # ── Computed helper for view logic ────────────────────────────────────────

    payment_required = fields.Boolean(
        string='Payment Required',
        compute='_compute_payment_required',
        store=False,
    )

    @api.depends('decision', 'join_timing')
    def _compute_payment_required(self):
        """Payment is mandatory ONLY when student is joining AND timing is 'Now'."""
        for rec in self:
            rec.payment_required = (
                rec.decision == 'joining' and rec.join_timing == 'now'
            )

    # ── Onchange: join_timing → expected_join_date ────────────────────────────

    _TIMING_DAYS = {
        'now':      0,
        '1_week':   7,
        '2_weeks':  14,
        '1_month':  30,
        '3_months': 90,
    }

    @api.onchange('join_timing')
    def _onchange_join_timing(self):
        if self.join_timing and self.join_timing != 'later':
            days = self._TIMING_DAYS.get(self.join_timing, 0)
            self.expected_join_date = date.today() + timedelta(days=days)
        else:
            self.expected_join_date = False

    @api.onchange('payment_type')
    def _onchange_payment_type_full(self):
        """Full payment always means the student starts now.

        Join Timing is hidden in that case, so force a consistent value
        (the field is required and would otherwise block the confirmation).
        """
        if self.payment_type == 'full':
            self.join_timing = 'now'
            self.expected_join_date = date.today()

    # ── Confirm Action ────────────────────────────────────────────────────────

    def action_confirm(self):
        """Persist assessment data to the lesson and mark it as completed."""
        self.ensure_one()
        lesson = self.lesson_id

        if lesson.state != 'planned':
            raise UserError(_('Only planned lessons can be marked as completed.'))

        if not self.decision:
            raise UserError(_('Please select the Student Decision before completing the lesson.'))

        # Payment is only mandatory when joining AND timing is "Now"
        payment_required = (self.decision == 'joining' and self.join_timing == 'now')
        if payment_required:
            if not self.payment_type:
                raise UserError(_('Payment Type is required when the student decides to join now.'))
            if not self.payment_amount or self.payment_amount <= 0:
                raise UserError(_(
                    'Payment Amount is required and must be greater than zero '
                    'when the student decides to join now.'
                ))

        # Write all assessment fields back to the lesson
        lesson.write({
            'lesson_company_id':    self.lesson_company_id.id,
            'position_id':          self.position_id.id,
            'school_id':            self.school_id.id,
            'gender':               self.gender,
            'approximate_age':      self.approximate_age,
            'english_level':        self.english_level,
            'comprehension':        self.comprehension,
            'motivation':           self.motivation,
            'learning_purpose_id':  self.learning_purpose_id.id,
            'previous_courses':     self.previous_courses,
            'course_id':            self.course_id.id,
            'for_whom':             self.for_whom,
            'for_whom_note':        self.for_whom_note,
            'decision':             self.decision,
            'thinking_reason':      self.thinking_reason,
            'system_choice':        self.system_choice,
            'system_choice_note':   self.system_choice_note,
            'lesson_format':        self.lesson_format,
            'payment_type':         self.payment_type,
            'payment_amount':       self.payment_amount,
            'join_timing':          self.join_timing,
            'expected_join_date':   self.expected_join_date,
            'complete_notes':       self.wizard_notes,
        })

        # Replace persistent Q&A lines with wizard lines
        lesson.qa_ids.unlink()
        for qa in self.qa_ids:
            self.env['trail.lesson.qa'].create({
                'lesson_id':   lesson.id,
                'sequence':    qa.sequence,
                'question':    qa.question,
                'answer':      qa.answer,
                'translation': qa.translation,
            })

        # Close any open activities on this lesson
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'trail.lesson'),
            ('res_id', '=', lesson.id),
        ])
        activities.action_done()

        lesson.state = 'completed'

        partner = lesson.student_id

        # ── Will Join + Now → convert to Student ─────────────────────────────
        if self.decision == 'joining' and self.join_timing == 'now':
            if partner:
                vals = {
                    'is_student':         True,
                    'is_applicant':       False,
                    'expected_join_date': self.expected_join_date,
                }
                if partner.is_applicant:
                    vals['applicant_state'] = 'paid'
                    partner.activity_ids.action_done()
                partner.write(vals)

        # ── Will Join (later) OR Still Thinking → set applicant to Remember ──
        elif self.decision in ('joining', 'thinking'):
            if partner:
                vals = {'expected_join_date': self.expected_join_date}
                if partner.is_applicant:
                    vals['applicant_state'] = 'remember'
                partner.write(vals)

        # ── Will Not Join → just save expected date if provided ───────────────
        elif self.expected_join_date:
            if partner:
                partner.expected_join_date = self.expected_join_date

        return {'type': 'ir.actions.act_window_close'}