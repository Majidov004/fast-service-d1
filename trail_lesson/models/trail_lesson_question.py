# -*- coding: utf-8 -*-
from odoo import models, fields, api

# ── Shared selections ────────────────────────────────────────────────────────
# Kept in one place so the lesson, the complete wizard, the question bank and
# the training group all speak about the very same programs / levels.
# NOTE: the stored keys stay `system_1..3` so existing records keep working —
# only the labels changed (Essentials / Forward / Acceleration).

SYSTEM_SELECTION = [
    ('system_1', 'Essentials Program'),
    ('system_2', 'Forward Program'),
    ('system_3', 'Acceleration Program'),
    ('system_4', 'Old Program'),
    ('speaking', 'Speaking'),
    ('other', 'Other'),
]

LEVEL_SELECTION = [
    ('a1', 'A1 – Beginner'),
    ('a2', 'A2 – Elementary'),
    ('b1', 'B1 – Pre-Intermediate'),
    ('b2', 'B2 – Intermediate'),
    ('c1', 'C1 – Advanced'),
    ('c2', 'C2 – Proficiency'),
]

STAGE_SELECTION = [
    ('trial', 'Trial Lesson'),
    ('exam', 'Exam'),
]


class TrailLessonQuestion(models.Model):
    """Central question bank.

    One table holds every question we ask a student — both the ones used in the
    trial lesson (Complete Trial wizard) and the ones used in the exams every
    5 lessons (training_exam). `stage` tells them apart, `level` / `system_choice`
    / `exam_number` narrow down which questions are pulled where.

    An empty `level` / `system_choice` means "applies to all of them".
    """
    _name = 'trail.lesson.question'
    _description = 'Question Bank (Trial & Exam)'
    _order = 'stage, exam_number, sequence, id'

    name = fields.Char(
        string='Title',
        required=True,
        help='Short heading of the question, e.g. "Daily routine".',
    )
    question = fields.Text(
        string='Question',
        required=True,
        help='The question text asked to the student.',
    )
    translation = fields.Char(string='Translation (AZ/RU)')
    stage = fields.Selection(
        selection=STAGE_SELECTION,
        string='Stage',
        default='trial',
        required=True,
        help='Trial Lesson → shown in the Complete Trial wizard.\n'
             'Exam → shown in the exam popup of a training group.',
    )
    exam_number = fields.Integer(
        string='Exam #',
        help='Which exam this question belongs to (1 = after lesson 5, '
             '2 = after lesson 10, …). Leave 0 to use it in every exam.',
    )
    level = fields.Selection(
        selection=LEVEL_SELECTION,
        string='Level',
        help='Leave empty to make the question available on every level.',
    )
    system_choice = fields.Selection(
        selection=SYSTEM_SELECTION,
        string='Program / System',
        help='Leave empty to make the question available in every program.',
    )
    note = fields.Text(
        string='Details / Expected Answer',
        help='Internal note for the teacher: expected answer, grammar point, etc.',
    )
    sequence = fields.Integer(string='#', default=10)
    active = fields.Boolean(string='Active', default=True)

    def _display_question(self):
        """Text pushed into a Q&A line — falls back to the title."""
        self.ensure_one()
        return (self.question or self.name or '').strip()

    @api.model
    def fetch_questions(self, stage, level=None, exam_number=None, system=None):
        """Return the active questions matching a stage (+ optional filters).

        Empty `level` / `system_choice` on a question = "matches anything",
        so generic questions always come along with the specific ones.
        """
        domain = [('stage', '=', stage)]
        if level:
            domain += ['|', ('level', '=', False), ('level', '=', level)]
        if system:
            domain += ['|', ('system_choice', '=', False), ('system_choice', '=', system)]
        if exam_number:
            domain += ['|', ('exam_number', 'in', (0, False)), ('exam_number', '=', exam_number)]
        return self.search(domain)
