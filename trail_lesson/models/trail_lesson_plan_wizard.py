# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class TrailLessonPlanWizard(models.TransientModel):
    """Quick wizard to plan a new trial lesson.
    Opened via 'Plan New Trial' button; pre-fills the student from context.
    """
    _name = 'trail.lesson.plan.wizard'
    _description = 'Plan New Trial Lesson Wizard'

    student_id = fields.Many2one(
        comodel_name='res.partner',
        string='Student',
        required=True,
    )
    teacher_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Trial Teacher',
        required=True,
    )
    lesson_datetime = fields.Datetime(
        string='Trial DateTime',
        required=True,
    )
    lesson_id = fields.Many2one(
        comodel_name='trail.lesson',
        string='Lesson (Modify Mode)',
        readonly=True,
    )

    def action_confirm(self):
        """Create a new lesson OR update + reschedule an existing planned one."""
        self.ensure_one()

        # ── Modify mode: update existing planned lesson ───────────────────────
        if self.lesson_id:
            lesson = self.lesson_id
            # Reset to not_planned so action_schedule can run
            lesson.write({
                'state': 'not_planned',
                'teacher_id': self.teacher_id.id,
                'lesson_datetime': self.lesson_datetime,
            })
            lesson.action_schedule()
            return {'type': 'ir.actions.act_window_close'}

        # ── Create mode: new lesson ───────────────────────────────────────────
        lesson = self.env['trail.lesson'].create({
            'teacher_id': self.teacher_id.id,
            'student_id': self.student_id.id,
            'lesson_datetime': self.lesson_datetime,
        })
        return {
            'name': _('Trial Lesson'),
            'type': 'ir.actions.act_window',
            'res_model': 'trail.lesson',
            'res_id': lesson.id,
            'view_mode': 'form',
            'target': 'current',
        }