# -*- coding: utf-8 -*-
from odoo import models, fields


class LanguageLevel(models.Model):
    _name = 'hr.language.level'
    _description = 'Language Level'
    _order = 'name'

    name = fields.Char(string='Level', required=True)
    active = fields.Boolean(default=True)