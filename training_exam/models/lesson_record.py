from odoo import models


class LessonRecord(models.Model):
    _inherit = 'lesson.record'

    def action_complete_lesson(self):
        res = super().action_complete_lesson()
        self._check_exam_ready()
        return res

    def _check_exam_ready(self):
        """When a milestone lesson (every 5th) is completed, the matching exam
        becomes 'ready' and the exam teacher is notified."""
        for lesson in self:
            if lesson.state != 'completed':
                continue
            if not lesson.lesson_number or lesson.lesson_number % 5 != 0:
                continue
            exam = self.env['training.exam'].search([
                ('group_id', '=', lesson.group_id.id),
                ('after_lesson_number', '=', lesson.lesson_number),
                ('state', '=', 'waiting'),
            ], limit=1)
            if exam:
                exam.action_set_ready()
