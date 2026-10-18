# -*- coding: utf-8 -*-
from odoo import models, fields


class ContactNoteWizard(models.TransientModel):
    _name = 'contact.note.wizard'
    _description = 'Add / Edit Contact Note'

    partner_id = fields.Many2one('res.partner', required=True)
    note_id = fields.Many2one('contact.note')
    employee_id = fields.Many2one(
        'hr.employee',
        string='Author',
        required=True,
        default=lambda self: self.env.user.employee_id,
    )
    text = fields.Text(string='Note', required=True)

    def action_save(self):
        self.ensure_one()
        if self.note_id:
            self.note_id.write({'text': self.text})
        else:
            self.env['contact.note'].create({
                'partner_id': self.partner_id.id,
                'employee_id': self.employee_id.id,
                'text': self.text,
            })
        return {'type': 'ir.actions.act_window_close'}
