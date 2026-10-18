# -*- coding: utf-8 -*-
from odoo import models, fields


class HrEmployeeCertificate(models.Model):
    """Müəllimin sertifikatları. `certificate_id` → hr.certificate.type (lookup),
    `issued_by_id` → mövcud trail.lesson.config.school lookup."""
    _name = 'hr.employee.certificate'
    _description = 'Employee Certificate'
    _order = 'id'

    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True, ondelete='cascade')
    certificate_id = fields.Many2one('hr.certificate.type', string='Certificate')
    issued_by_id = fields.Many2one('trail.lesson.config.school', string='Issued By')
    year = fields.Char(string='Year')
