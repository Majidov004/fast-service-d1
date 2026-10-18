# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartnerNote(models.Model):
    _inherit = 'res.partner'

    note_ids = fields.One2many('contact.note', 'partner_id', string='Notes')

    def action_open_add_note_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Add Note',
            'res_model': 'contact.note.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
            },
        }
