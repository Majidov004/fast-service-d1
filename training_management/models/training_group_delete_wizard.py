from odoo import models, fields, api


class TrainingGroupDeleteWizard(models.TransientModel):
    _name = 'training.group.delete.wizard'
    _description = 'Training Group Delete Wizard'

    group_id = fields.Many2one(
        'training.group',
        string='Training Group',
        readonly=True
    )

    lesson_count = fields.Integer(
        string='Lesson Record Count',
        readonly=True
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        group_id = res.get('group_id') or self.env.context.get('active_id')
        if group_id:
            res['group_id'] = group_id
            res['lesson_count'] = self.env['lesson.record'].search_count(
                [('group_id', '=', group_id)]
            )
        return res

    def action_confirm_delete(self):
        lesson_records = self.env['lesson.record'].search(
            [('group_id', '=', self.group_id.id)]
        )
        lesson_records.unlink()
        self.group_id.with_context(bypass_lesson_check=True).unlink()
        return {'type': 'ir.actions.act_window_close'}