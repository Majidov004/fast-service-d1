# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    finance_default_register_id = fields.Many2one(
        'finance.cash.register', string='Default Cash Register',
        config_parameter='finance.default_register_id',
        help='Default register pre-selected when an applicant is converted into a student.')
    finance_student_payment_category_id = fields.Many2one(
        'finance.category', string='Student Payment Category',
        config_parameter='finance.student_payment_category_id',
        help='Income category used for the auto-created Cash In when an applicant pays.')
