# -*- coding: utf-8 -*-
from odoo import models, fields


class EmployeeAvailability(models.Model):
    _name = 'hr.employee.availability'
    _description = 'Employee Availability'
    _order = 'day_of_week, time_from'

    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
    )

    day_of_week = fields.Selection(
        selection=[
            ('0', 'Monday'),
            ('1', 'Tuesday'),
            ('2', 'Wednesday'),
            ('3', 'Thursday'),
            ('4', 'Friday'),
            ('5', 'Saturday'),
            ('6', 'Sunday'),
        ],
        string='Day',
        required=True,
    )

    time_from = fields.Float(
        string='From',
        required=True,
    )

    time_to = fields.Float(
        string='To',
        required=True,
    )