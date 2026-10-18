# -*- coding: utf-8 -*-
from odoo import models, fields


class HrEmployeeLanguage(models.Model):
    """Hansı dili hansı səviyyədə bilir — müəllimin dil biliyi sətri.
    `language_id` → hr.language (lookup, yoxdursa OWL widget dərhal yaradır),
    `level_id` → mövcud hr.language.level lookup."""
    _name = 'hr.employee.language'
    _description = 'Employee Language Knowledge'
    _order = 'id'

    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True, ondelete='cascade')
    language_id = fields.Many2one('hr.language', string='Language')
    level_id = fields.Many2one('hr.language.level', string='Level')
