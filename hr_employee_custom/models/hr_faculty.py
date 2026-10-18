# -*- coding: utf-8 -*-
from odoo import models, fields


class HrFaculty(models.Model):
    """Fakültə lookup-u. Many2one olduğu üçün formada Odoo-nun öz dropdown +
    'Create' funksiyası ilə seçilir/yaradılır."""
    _name = 'hr.faculty'
    _description = 'Faculty'
    _order = 'name'

    name = fields.Char(string='Faculty', required=True)
    active = fields.Boolean(default=True)
