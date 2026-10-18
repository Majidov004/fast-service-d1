# -*- coding: utf-8 -*-
from odoo import models, fields


class HrLanguage(models.Model):
    """Dil lookup-u (İngilis, Rus, …). OWL widget seçim siyahısında olmayanı
    dərhal yarada bilir."""
    _name = 'hr.language'
    _description = 'Language'
    _order = 'name'

    name = fields.Char(string='Language', required=True)
    active = fields.Boolean(default=True)
