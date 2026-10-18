from odoo import models, fields

from odoo.addons.trail_lesson.models.trail_lesson_question import SYSTEM_SELECTION


class TrainingGroup(models.Model):
    _inherit = 'training.group'

    exam_teacher_id = fields.Many2one('hr.employee', string='Exam Teacher')
    system_choice = fields.Selection(
        SYSTEM_SELECTION,
        string='Program / System',
        help='Which program this group follows. It decides which exam questions '
             'are pulled from the Question Bank (Trail Lesson → Configurator).',
    )

    # Mount point for the OWL Exam widget (no real data; widget loads via RPC)
    exam_view = fields.Char(string='Exam', compute='_compute_exam_view')

    def _compute_exam_view(self):
        for record in self:
            record.exam_view = False

    # ── Exam generation ──────────────────────────────────────────────────────

    def action_start(self):
        res = super().action_start()
        for record in self:
            record._generate_exams()
        return res

    def _generate_exams(self):
        """One exam per 5 lessons (20 lessons → 4 exams). Remainder < 5 is skipped."""
        self.ensure_one()
        if self.env['training.exam'].search_count([('group_id', '=', self.id)]):
            return  # already generated

        exam_number = 0
        for lesson_n in range(5, self.lesson_count + 1, 5):
            exam_number += 1
            exam = self.env['training.exam'].create({
                'name': f'{self.name} — Exam {exam_number} (after Lesson {lesson_n})',
                'group_id': self.id,
                'exam_number': exam_number,
                'after_lesson_number': lesson_n,
            })
            for student_line in self.student_line_ids:
                self.env['training.exam.student.line'].create({
                    'exam_id': exam.id,
                    'student_id': student_line.student_id.id,
                })

    # ── Exam tab (OWL widget RPC) ────────────────────────────────────────────

    def get_exam_cards(self):
        """Mini exam cards for the Exam tab (this group's exams)."""
        self.ensure_one()
        exams = self.env['training.exam'].search(
            [('group_id', '=', self.id)], order='exam_number asc'
        )
        return [{
            'id': exam.id,
            'name': exam.name,
            'exam_number': exam.exam_number,
            'after_lesson_number': exam.after_lesson_number,
            'state': exam.state,
            'student_count': exam.student_count,
            'weak_count': exam.weak_count,
        } for exam in exams]

    def get_exam_detail(self, exam_id):
        """Full exam detail for the popup: per student the bank questions
        (left pane) plus the result and the comment (right pane)."""
        self.ensure_one()
        exam = self.env['training.exam'].browse(exam_id)
        if not exam.exists() or exam.group_id.id != self.id:
            return {}

        # Pull any newly configured question into the exam (never on a done exam).
        exam._sync_questions()

        students = [{
            'line_id': line.id,
            'student_id': line.student_id.id,
            'student_name': line.student_id.name or '',
            'result': line.result or '',
            'note': line.note or '',
            'answers': [{
                'answer_id': answer.id,
                'question': answer.question or '',
                'answer': answer.answer or '',
            } for answer in line.answer_ids],
        } for line in exam.student_line_ids]
        return {
            'id': exam.id,
            'name': exam.name,
            'exam_number': exam.exam_number,
            'after_lesson_number': exam.after_lesson_number,
            'state': exam.state,
            'system_choice': exam.group_id.system_choice or '',
            'students': students,
        }

    def save_exam(self, exam_id, payload):
        """Persist answers, results + comments from the popup; optionally complete."""
        self.ensure_one()
        exam = self.env['training.exam'].browse(exam_id)
        if not exam.exists() or exam.group_id.id != self.id:
            return self.get_exam_cards()

        payload = payload or {}

        for student in payload.get('students', []):
            line = self.env['training.exam.student.line'].browse(student.get('line_id'))
            if not line.exists() or line.exam_id.id != exam.id:
                continue
            line.write({
                'result': student.get('result') or False,
                'note': student.get('note') or False,
            })
            for answer in student.get('answers', []):
                record = self.env['training.exam.answer'].browse(answer.get('answer_id'))
                if not record.exists() or record.line_id.id != line.id:
                    continue
                record.answer = answer.get('answer') or False

        if payload.get('complete'):
            exam._mark_done_and_notify()

        return self.get_exam_cards()
