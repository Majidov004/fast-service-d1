# -*- coding: utf-8 -*-
from odoo import models, fields


class HrEmployeeExperience(models.Model):
    """İş / könüllü / ingilisdilli müəllimlik təcrübəsi — hamısı bir model,
    `kind` ilə ayrılır. `place_id` (harda) və `role_id` (nə iş) mövcud
    trail_lesson lookup-larını təkrar istifadə edir; `duration` sərbəst mətndir."""
    _name = 'hr.employee.experience'
    _description = 'Employee Experience'
    _order = 'id'

    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True, ondelete='cascade')
    kind = fields.Selection(
        selection=[
            ('work', 'Work'),
            ('volunteer', 'Volunteer'),
            ('english_teaching', 'English Teaching'),
        ],
        string='Kind', required=True, default='work')
    place_id = fields.Many2one('trail.lesson.config.company', string='Place')
    role_id = fields.Many2one('trail.lesson.config.position', string='Role / What')
    duration = fields.Char(string='Duration')
