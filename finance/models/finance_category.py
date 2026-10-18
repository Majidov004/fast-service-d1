# -*- coding: utf-8 -*-
from odoo import models, fields


class FinanceCategory(models.Model):
    """Income / Expense groups. `detail_type` drives which cascading detail field
    appears on the cash move (expense item / employee / student / partner / none)."""
    _name = 'finance.category'
    _description = 'Finance Category'
    _order = 'direction, name'

    name = fields.Char(string='Name', required=True)
    direction = fields.Selection(
        selection=[('income', 'Income (Gəlir)'), ('expense', 'Expense (Xərc)')],
        string='Direction', required=True, default='expense',
    )
    detail_type = fields.Selection(
        selection=[
            ('none', 'None'),
            ('expense', 'Expense Item'),
            ('employee', 'Employee'),
            ('student', 'Student'),
            ('partner', 'Partner'),
        ],
        string='Detail Type', required=True, default='none',
        help='Which extra field opens on the document when this category is selected.',
    )
    active = fields.Boolean(default=True)
