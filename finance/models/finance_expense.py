# -*- coding: utf-8 -*-
from odoo import models, fields


class FinanceExpense(models.Model):
    """Expense items ("Xərc Modulu") selected when a Cash Out category is 'expense'."""
    _name = 'finance.expense'
    _description = 'Expense Item'
    _order = 'name'

    name = fields.Char(string='Expense Item', required=True)
    note = fields.Char(string='Note')
    active = fields.Boolean(default=True)
