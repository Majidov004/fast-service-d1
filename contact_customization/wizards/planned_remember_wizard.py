# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PlannedRememberWizard(models.TransientModel):
    _name = 'res.partner.planned.remember.wizard'
    _description = 'Planned Remember Wizard'

    partner_id = fields.Many2one('res.partner', required=True)
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        readonly=True,
        required=True,
        default=lambda self: self.env.user.employee_id,
    )
    planned_date = fields.Date(string='Planned Date', required=True)

    def action_confirm(self):
        self.ensure_one()
        self.partner_id.write({
            'applicant_state': 'planned_remember',
            'planned_remember_date': self.planned_date,
            'planned_remember_employee_id': self.employee_id.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Planned Remember',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'res_id': self.partner_id.id,
            'target': 'current',
        }
