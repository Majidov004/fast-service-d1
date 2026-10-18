# -*- coding: utf-8 -*-
from odoo import models


class ResPartner(models.Model):
    """Finance hook on the applicant 'Paid' button: instead of converting the
    applicant straight away, open a dialog that lets the operator see the
    customer's current debt and optionally create a Student Charge and/or a
    Cash In. The actual conversion happens from the wizard with the
    `skip_finance_wizard` context flag, which routes back to the original
    implementation in contact_customization."""
    _inherit = 'res.partner'

    def action_set_paid(self):
        if self.env.context.get('skip_finance_wizard'):
            return super().action_set_paid()
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Convert to Student',
            'res_model': 'finance.applicant.paid.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_partner_id': self.id},
        }
