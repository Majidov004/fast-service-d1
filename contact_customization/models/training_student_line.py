# -*- coding: utf-8 -*-
from odoo import models, api


class TrainingStudentLine(models.Model):
    """Enrolling a waiting student into a group ends the waiting period."""
    _inherit = 'training.student.line'

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        waiting = lines.mapped('student_id').filtered('is_waiting_student')
        if waiting:
            waiting.write({'is_waiting_student': False})
        return lines

    def write(self, vals):
        res = super().write(vals)
        if vals.get('student_id'):
            waiting = self.mapped('student_id').filtered('is_waiting_student')
            if waiting:
                waiting.write({'is_waiting_student': False})
        return res
