# -*- coding: utf-8 -*-
from markupsafe import Markup
from odoo import models, _


class TrailLessonCompleteWizardWaiting(models.TransientModel):
    """Waiting-student extension of the trial-completion wizard.

    Base behaviour (trail_lesson): "Will Join" with a timing other than *Now*
    only sets the applicant to `remember`. But when the person actually paid
    (deposit or full) and simply starts later, they are already a customer —
    so they become a **student** flagged as *waiting* until a training group
    picks them up.
    """
    _inherit = 'trail.lesson.complete.wizard'

    def action_confirm(self):
        res = super().action_confirm()
        for wizard in self:
            wizard._apply_waiting_student()
        return res

    def _apply_waiting_student(self):
        self.ensure_one()
        if self.decision != 'joining' or self.join_timing == 'now':
            return
        if (self.payment_amount or 0.0) <= 0.0:
            return
        partner = self.lesson_id.student_id
        if not partner:
            return

        vals = {
            'is_student':         True,
            'is_waiting_student': True,
            'expected_join_date': self.expected_join_date,
        }
        if partner.is_applicant:
            vals['is_applicant'] = False
            vals['applicant_state'] = 'paid'
            partner.activity_ids.action_done()
        partner.write(vals)

        note = _(
            'Paid during the trial lesson but starts later — moved to '
            'Waiting Students (expected: %s).'
        ) % (self.expected_join_date or _('date not set'))
        partner.message_post(body=Markup('<p>%s</p>') % note)
