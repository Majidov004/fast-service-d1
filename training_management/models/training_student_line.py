from odoo import models, fields, api


class TrainingStudentLine(models.Model):
    _name = 'training.student.line'
    _description = 'Training Student Line'
    _rec_name = 'student_id'

    group_id = fields.Many2one(
        'training.group',
        string='Training Group',
        required=True,
        ondelete='cascade'
    )
    
    student_id = fields.Many2one(
        'res.partner',
        string='Student',
        required=True,
        domain=[('is_student', '=', True)]
    )
    
    phone = fields.Char(
        string='Phone',
        related='student_id.phone',
        readonly=True
    )
    
    mobile = fields.Char(
        string='Mobile',
        related='student_id.mobile',
        readonly=True
    )
    
    lesson_count = fields.Integer(
        string='Lesson Count',
        required=True,
        default=1
    )
    
    @api.onchange('group_id')
    def _onchange_group_id(self):
        """Set default lesson count from group"""
        if self.group_id and self.group_id.lesson_count:
            self.lesson_count = self.group_id.lesson_count
    
    _sql_constraints = [
        ('unique_student_group', 
         'UNIQUE(group_id, student_id)', 
         'A student cannot be added to the same group twice!')
    ]