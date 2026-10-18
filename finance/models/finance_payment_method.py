# -*- coding: utf-8 -*-
from odoo import models, fields


class FinancePaymentMethod(models.Model):
    _name = 'finance.payment.method'
    _description = 'Payment Method'
    _order = 'sequence, name'

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
