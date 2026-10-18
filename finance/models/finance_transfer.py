# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class FinanceTransfer(models.Model):
    """Move money from one cash register to another. `amount` leaves the source in
    its currency; `amount_to` is the converted amount received by the destination."""
    _name = 'finance.transfer'
    _description = 'Cash Transfer'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', default='New', readonly=True, copy=False)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    from_register_id = fields.Many2one('finance.cash.register', string='From Register', required=True, tracking=True)
    to_register_id = fields.Many2one('finance.cash.register', string='To Register', required=True, tracking=True)
    from_currency_id = fields.Many2one(related='from_register_id.currency_id', string='From Currency', store=True, readonly=True)
    to_currency_id = fields.Many2one(related='to_register_id.currency_id', string='To Currency', store=True, readonly=True)

    amount = fields.Monetary(string='Amount Sent', required=True, currency_field='from_currency_id', tracking=True)
    amount_to = fields.Monetary(
        string='Amount Received', compute='_compute_amount_to', store=False,
        currency_field='to_currency_id',
        help='Amount sent converted into the destination register currency '
             '(rate for the transfer date). Not stored — reflects the current rate.')

    note = fields.Text(string='Note')
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('confirmed', 'Confirmed'), ('cancelled', 'Cancelled')],
        string='Status', default='draft', required=True, tracking=True, copy=False)

    @api.depends('amount', 'from_currency_id', 'to_currency_id')
    def _compute_amount_to(self):
        for rec in self:
            if rec.amount and rec.from_currency_id and rec.to_currency_id:
                rec.amount_to = rec.from_currency_id.finance_convert(
                    rec.amount, rec.to_currency_id)
            else:
                rec.amount_to = 0.0

    @api.constrains('from_register_id', 'to_register_id')
    def _check_registers(self):
        for rec in self:
            if rec.from_register_id and rec.from_register_id == rec.to_register_id:
                raise ValidationError(_('Source and destination registers must be different.'))

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_('Amount must be greater than zero.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('finance.transfer') or 'New'
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft transfers can be confirmed.'))
            rec.state = 'confirmed'

    def action_draft(self):
        for rec in self:
            if rec.state == 'confirmed':
                rec.state = 'draft'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'
