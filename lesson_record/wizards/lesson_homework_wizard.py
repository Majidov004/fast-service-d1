from odoo import models, fields, api


class LessonHomeworkWizard(models.TransientModel):
    _name = 'lesson.homework.wizard'
    _description = 'Lesson Homework Wizard'

    student_line_id = fields.Many2one(
        'lesson.student.line',
        string='Student Line',
        required=True
    )

    student_id = fields.Many2one(
        'res.partner',
        string='Student',
        related='student_line_id.student_id',
        readonly=True
    )

    lesson_id = fields.Many2one(
        'lesson.record',
        string='Lesson',
        related='student_line_id.lesson_id',
        readonly=True
    )

    attachment_ids = fields.Many2many(
        'ir.attachment',
        'lesson_homework_wizard_attachment_rel',
        'wizard_id',
        'attachment_id',
        string='Homework Files'
    )

    @api.model
    def default_get(self, fields_list):
        """Mövcud attachmentləri wizard açılanda yüklə"""
        res = super().default_get(fields_list)
        line_id = self.env.context.get('default_student_line_id')
        if line_id:
            line = self.env['lesson.student.line'].browse(line_id)
            res['attachment_ids'] = [(6, 0, line.homework_attachment_ids.ids)]
        return res

    def action_save(self):
        """Dəyişiklikləri student line-a yazıb wizard-ı bağla"""
        self.student_line_id.homework_attachment_ids = self.attachment_ids
        return {'type': 'ir.actions.act_window_close'}

    def action_save_and_stay(self):
        """Yadda saxla və wizard-da qal"""
        self.student_line_id.homework_attachment_ids = self.attachment_ids
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.student_id.name} - Homework',
            'res_model': 'lesson.homework.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }