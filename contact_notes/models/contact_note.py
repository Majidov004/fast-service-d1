# -*- coding: utf-8 -*-
from odoo import models, fields


class ContactNote(models.Model):
    _name = 'contact.note'
    _description = 'Contact Note'
    _order = 'date desc, id desc'

    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Author', required=True)
    date = fields.Datetime(string='Date', default=fields.Datetime.now, readonly=True)
    text = fields.Text(string='Note', required=True)
