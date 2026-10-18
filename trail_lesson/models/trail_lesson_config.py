# -*- coding: utf-8 -*-
from odoo import models, fields


class TrailLessonConfigCompany(models.Model):
    _name = 'trail.lesson.config.company'
    _description = 'Trail Lesson – Company Options'
    _order = 'name'

    name = fields.Char(string='Company Name', required=True)
    active = fields.Boolean(default=True)


class TrailLessonConfigPosition(models.Model):
    _name = 'trail.lesson.config.position'
    _description = 'Trail Lesson – Position / Title Options'
    _order = 'name'

    name = fields.Char(string='Position / Title', required=True)
    active = fields.Boolean(default=True)


class TrailLessonConfigCourse(models.Model):
    _name = 'trail.lesson.config.course'
    _description = 'Trail Lesson – Course Options'
    _order = 'name'

    name = fields.Char(string='Course Name', required=True)
    active = fields.Boolean(default=True)


class TrailLessonConfigSchool(models.Model):
    _name = 'trail.lesson.config.school'
    _description = 'Trail Lesson – School Options'
    _order = 'name'

    name = fields.Char(string='School Name', required=True)
    active = fields.Boolean(default=True)


class TrailLessonConfigLearningPurpose(models.Model):
    _name = 'trail.lesson.config.learning.purpose'
    _description = 'Trail Lesson – Learning Purpose Options'
    _order = 'name'

    name = fields.Char(string='Learning Purpose', required=True)
    active = fields.Boolean(default=True)