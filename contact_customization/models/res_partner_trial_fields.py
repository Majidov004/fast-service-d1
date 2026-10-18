# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartnerTrialFields(models.Model):
    """Quick-plan fields shown in the Trial Lesson tab."""
    _inherit = 'res.partner'

    trial_teacher_id = fields.Many2one(
        'hr.employee',
        string='Trial Teacher',
    )
    trial_datetime = fields.Datetime(
        string='Trial Date & Time',
    )
