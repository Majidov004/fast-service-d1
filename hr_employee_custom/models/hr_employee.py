# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # ── Tədris qrupları (müəllim kimi) ──────────────────────────────────────
    x_group_ids = fields.One2many(
        comodel_name='training.group',
        inverse_name='teacher_id',
        string='Training Groups',
    )
    x_active_group_count = fields.Integer(
        string='Active Groups',
        compute='_compute_active_groups', store=True,
    )
    x_has_active_group = fields.Boolean(
        string='Has Active Group',
        compute='_compute_active_groups', store=True,
    )

    @api.depends('x_group_ids.state')
    def _compute_active_groups(self):
        for emp in self:
            active = emp.x_group_ids.filtered(lambda g: g.state == 'in_progress')
            emp.x_active_group_count = len(active)
            emp.x_has_active_group = bool(active)

    x_language_levels = fields.Many2many(
        comodel_name='hr.language.level',
        relation='hr_employee_language_level_rel',
        column1='employee_id',
        column2='level_id',
        string='Teaching Levels',
    )

    x_school_id = fields.Many2one(
        comodel_name='trail.lesson.config.school',
        string='School / University',
    )

    x_lesson_type = fields.Selection(
        selection=[
            ('individual', 'Individual'),
            ('group', 'Group'),
            ('both', 'Individual & Group'),
        ],
        string='Lesson Type',
    )

    x_availability_ids = fields.One2many(
        comodel_name='hr.employee.availability',
        inverse_name='employee_id',
        string='Available Days & Hours',
    )

    # ── Təhsil (universitet) ────────────────────────────────────────────────
    x_study_year = fields.Selection(
        selection=[
            ('1', '1st Year'),
            ('2', '2nd Year'),
            ('3', '3rd Year'),
            ('4', '4th Year'),
            ('5', '5th Year'),
            ('graduate', 'Graduate'),
        ],
        string='Course / Year',
    )
    x_faculty_id = fields.Many2one('hr.faculty', string='Faculty')

    x_start_date = fields.Date(
        string='Start Date',
    )

    x_notes = fields.Html(
        string='Notes',
    )

    # ── Müəllim sualları ────────────────────────────────────────────────────
    x_language_line_ids = fields.One2many(
        comodel_name='hr.employee.language',
        inverse_name='employee_id',
        string='Languages Known',
    )
    x_work_exp_ids = fields.One2many(
        comodel_name='hr.employee.experience',
        inverse_name='employee_id',
        domain=[('kind', '=', 'work')],
        string='Work Experience',
    )
    x_volunteer_ids = fields.One2many(
        comodel_name='hr.employee.experience',
        inverse_name='employee_id',
        domain=[('kind', '=', 'volunteer')],
        string='Volunteer Experience',
    )
    x_has_english_teaching = fields.Boolean(
        string='Has English Teaching Experience',
    )
    x_english_teaching_ids = fields.One2many(
        comodel_name='hr.employee.experience',
        inverse_name='employee_id',
        domain=[('kind', '=', 'english_teaching')],
        string='English Teaching Experience',
    )
    x_certificate_ids = fields.One2many(
        comodel_name='hr.employee.certificate',
        inverse_name='employee_id',
        string='Certificates',
    )
    x_strong_skills = fields.Html(string='Strong Skills & Knowledge')