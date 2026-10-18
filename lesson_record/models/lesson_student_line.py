from odoo import models, fields, api


class LessonStudentLine(models.Model):
    _name = 'lesson.student.line'
    _description = 'Lesson Student Line'
    _rec_name = 'student_id'

    lesson_id = fields.Many2one(
        'lesson.record',
        string='Lesson',
        required=True,
        ondelete='cascade'
    )

    student_id = fields.Many2one(
        'res.partner',
        string='Student',
        required=True,
        domain=[('is_company', '=', False)]
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

    attendance = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent')
    ], string='Attendance', default='present', required=True)

    comment = fields.Text(
        string='Comment'
    )

    comment_create_date = fields.Datetime(
        string='Comment Created On',
        readonly=True,
        copy=False
    )

    comment_write_date = fields.Datetime(
        string='Comment Last Edited On',
        readonly=True,
        copy=False
    )

    homework_attachment_ids = fields.Many2many(
        'ir.attachment',
        'lesson_student_line_attachment_rel',
        'student_line_id',
        'attachment_id',
        string='Homework Files'
    )

    homework_count = fields.Integer(
        string='Homework Files',
        compute='_compute_homework_count'
    )

    @api.depends('homework_attachment_ids')
    def _compute_homework_count(self):
        for record in self:
            record.homework_count = len(record.homework_attachment_ids)

    # ── COMMENT DATE STAMPING ───────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        now = fields.Datetime.now()
        for vals in vals_list:
            if vals.get('comment'):
                vals.setdefault('comment_create_date', now)
                vals.setdefault('comment_write_date', now)
        return super().create(vals_list)

    def write(self, vals):
        if 'comment' not in vals:
            return super().write(vals)
        now = fields.Datetime.now()
        new_comment = vals.get('comment') or ''
        for rec in self:
            rec_vals = dict(vals)
            if new_comment != (rec.comment or ''):
                rec_vals['comment_write_date'] = now
                if new_comment and not rec.comment_create_date:
                    rec_vals['comment_create_date'] = now
            super(LessonStudentLine, rec).write(rec_vals)
        return True

    def action_open_homework_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.student_id.name} - Homework',
            'res_model': 'lesson.homework.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_student_line_id': self.id,
            }
        }

    _sql_constraints = [
        ('unique_student_lesson',
         'UNIQUE(lesson_id, student_id)',
         'A student cannot be added to the same lesson twice!')
    ]