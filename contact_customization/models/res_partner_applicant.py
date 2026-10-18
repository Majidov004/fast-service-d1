# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResPartnerApplicant(models.Model):
    """Applicant status and workflow actions."""
    _inherit = 'res.partner'

    applicant_state = fields.Selection([
        ('interested',         'Interested'),
        ('needs_to_be_called', 'Needs to be Called'),
        ('called',             'Messaged'),
        ('wait',               'Wait'),
        ('no_answer',          'No Answer'),
        ('planned_trial',      'Planned Trial'),
        ('trial_no_contact',   'Trial – No Contact'),
        ('planned_remember',   'Planned Remember'),
        ('remember',           'Remember'),
        ('not_want',           'Not Want'),
        ('paid',               'Paid'),
    ], string='Applicant Status', tracking=True)

    planned_remember_date = fields.Date(string='Planned Remember Date', tracking=True)
    planned_remember_employee_id = fields.Many2one(
        'hr.employee',
        string='Planned By',
        tracking=True,
    )

    no_answer_type = fields.Selection([
        ('message_not_answered', 'Message is not answered'),
        ('before_trial',         'Before Trial Lesson'),
        ('after_trial',          'After Trial Lesson'),
    ], string='No Answer Type', tracking=True)

    no_answer_type_effective = fields.Selection([
        ('message_not_answered', 'Message is not answered'),
        ('before_trial',         'Before Trial Lesson'),
        ('after_trial',          'After Trial Lesson'),
    ], compute='_compute_no_answer_type_effective', string='No Answer Stage')

    @api.depends('applicant_state', 'no_answer_type')
    def _compute_no_answer_type_effective(self):
        for rec in self:
            if rec.applicant_state == 'trial_no_contact':
                rec.no_answer_type_effective = 'before_trial'
            elif rec.applicant_state == 'no_answer' and rec.no_answer_type:
                rec.no_answer_type_effective = rec.no_answer_type
            else:
                rec.no_answer_type_effective = False

    def action_open_planned_remember_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Planned Remember',
            'res_model': 'res.partner.planned.remember.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
            },
        }

    # ── Yeni applicant yarananda avtomatik aktivlik yarat ─────────────────────

    def _create_applicant_activity(self):
        """Applicant üçün aktivlik yarat — badge görünsün."""
        activity_type = self.env.ref(
            'mail.mail_activity_data_call', raise_if_not_found=False
        ) or self.env['mail.activity.type'].search(
            [('name', 'ilike', 'call')], limit=1
        ) or self.env['mail.activity.type'].search([], limit=1)

        if not activity_type:
            return

        for rec in self:
            if not rec.is_applicant:
                continue
            existing = self.env['mail.activity'].search([
                ('res_model', '=', 'res.partner'),
                ('res_id', '=', rec.id),
                ('activity_type_id', '=', activity_type.id),
            ], limit=1)
            if not existing:
                rec.activity_schedule(
                    activity_type_id=activity_type.id,
                    summary=_('Call applicant: %s') % rec.name,
                    note=_('New applicant added. Please contact them.'),
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_applicant') and not vals.get('applicant_state'):
                vals['applicant_state'] = 'interested'
        records = super().create(vals_list)
        applicants = records.filtered(lambda r: r.is_applicant)
        if applicants:
            applicants._create_applicant_activity()
        return records

    # ── Status transition buttons ─────────────────────────────────────────────

    def action_set_wait(self):
        for rec in self:
            rec.applicant_state = 'wait'

    def action_set_needs_to_be_called(self):
        for rec in self:
            if not rec.trial_teacher_id:
                raise UserError(_(
                    'Please assign a Trial Teacher before setting status to "Needs to be Called".'
                ))
            rec.applicant_state = 'needs_to_be_called'

    def action_set_called(self):
        for rec in self:
            rec.applicant_state = 'called'
            rec.activity_ids.filtered(
                lambda a: a.res_model == 'res.partner'
            ).action_done()

    def action_set_no_answer(self):
        for rec in self:
            rec.applicant_state = 'no_answer'
            rec.no_answer_type = 'message_not_answered'

    def action_set_trial_no_contact(self):
        for rec in self:
            rec.applicant_state = 'no_answer'
            rec.no_answer_type = 'before_trial'

    def action_set_remember(self):
        """Sonradan xatırlatmaq üçün qeyd edilib."""
        for rec in self:
            rec.applicant_state = 'remember'

    def action_set_not_want(self):
        """Muracietci derse qatilmaq istemiyor."""
        for rec in self:
            rec.applicant_state = 'not_want'
            rec.activity_ids.action_done()

    def action_set_paid(self):
        """
        Applicant ödəniş etdikdə:
          - applicant_state → 'paid'
          - is_applicant    → False
          - is_student      → True
        """
        for rec in self:
            rec.applicant_state = 'paid'
            rec.is_applicant = False
            rec.is_student = True
            rec.activity_ids.action_done()

    def action_trial_complete(self):
        self.ensure_one()
        if not self.trial_lesson_id:
            raise UserError(_('No trial lesson found.'))
        return self.trial_lesson_id.action_complete()

    def action_trial_missing(self):
        self.ensure_one()
        if not self.trial_lesson_id:
            raise UserError(_('No trial lesson found.'))
        return self.trial_lesson_id.action_missing()

    def action_trial_plan_new(self):
        self.ensure_one()
        if not self.trial_lesson_id:
            raise UserError(_('No trial lesson found.'))
        return self.trial_lesson_id.action_plan_new_trial()

    def action_create_trial_lesson(self):
        """Create a Trail Lesson from the applicant and move to Planned Trial."""
        for rec in self:
            if not rec.trial_teacher_id:
                raise UserError(_(
                    'Please assign a Trial Teacher before creating a trial lesson.'
                ))
            if not rec.trial_datetime:
                raise UserError(_(
                    'Please set the Trial Date & Time before creating a trial lesson.'
                ))
            lesson = self.env['trail.lesson'].create({
                'student_id': rec.id,
                'teacher_id': rec.trial_teacher_id.id,
                'lesson_datetime': rec.trial_datetime,
            })
            if rec.trial_datetime:
                lesson.action_schedule()

            rec.applicant_state = 'planned_trial'
            # ✅ FIX: Trail Lesson formu avtomatik açılmır — sadəcə yaranır