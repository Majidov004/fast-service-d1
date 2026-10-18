# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    onboarding_done = fields.Boolean(
        string='Onboarding Done',
        compute='_compute_onboarding_done',
        inverse='_inverse_onboarding_done',
        store=False,
    )

    def _compute_onboarding_done(self):
        for rec in self:
            rec.onboarding_done = rec.user_id.onboarding_done if rec.user_id else True

    def _inverse_onboarding_done(self):
        for rec in self:
            if rec.user_id:
                rec.user_id.sudo().onboarding_done = rec.onboarding_done

    def action_complete_onboarding(self):
        """
        Mark onboarding as done:
        - Remove the forced action_id redirect from the user
        - Set onboarding_done = True
        - Redirect to the Home menu (normal Odoo flow)
        """
        self.ensure_one()
        user = self.user_id
        if user:
            # Remove the temporary redirect action
            old_action = user.sudo().action_id
            user.sudo().write({
                'action_id': False,
                'onboarding_done': True,
            })
            # Delete the temporary action we created
            if old_action and old_action.name == 'Complete My Profile':
                old_action.sudo().unlink()

        self.message_post(
            body=_('<b>✅ Onboarding completed.</b> Employee profile has been filled in.'),
            subtype_xmlid='mail.mt_note',
        )

        # Redirect to home after completion
        return {
            'type': 'ir.actions.client',
            'tag': 'home',
        }
