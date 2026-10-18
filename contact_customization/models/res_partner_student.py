# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartnerStudent(models.Model):
    """Student lesson-status and workflow actions."""
    _inherit = 'res.partner'

    lead_state = fields.Selection([
        ('lesson_not_planned', 'Lesson not Planned'),
        ('lesson_planned',     'Lesson is Planned'),
        ('lesson_complete',    'Lesson Complete'),
    ], string='Lesson Status', default='lesson_not_planned', tracking=True)

    # ── Waiting students ──────────────────────────────────────────────────────
    # A student who already paid (deposit/full) during the trial but starts
    # later — they exist as a student but belong to no training group yet.
    is_waiting_student = fields.Boolean(
        string='Waiting Student',
        default=False,
        tracking=True,
        help='The student paid but the start date is in the future. '
             'Cleared automatically as soon as they are added to a training group.',
    )

    # ── Status transition buttons ─────────────────────────────────────────────

    def action_set_lesson_planned(self):
        for rec in self:
            rec.lead_state = 'lesson_planned'

    def action_set_lesson_complete(self):
        for rec in self:
            rec.lead_state = 'lesson_complete'
