# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class FinanceCashMove(models.Model):
    """Cash In / Cash Out document. One register, document currency (defaults to the
    register currency). `amount_register` is the amount converted into the register
    currency — the real money entering/leaving the register."""
    _name = 'finance.cash.move'
    _description = 'Cash Move'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', default='New', readonly=True, copy=False, index=True)
    move_type = fields.Selection(
        selection=[('cash_in', 'Cash In'), ('cash_out', 'Cash Out')],
        string='Type', required=True, default='cash_in', tracking=True,
    )
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    register_id = fields.Many2one('finance.cash.register', string='Cash Register', required=True, tracking=True)
    register_currency_id = fields.Many2one(
        related='register_id.currency_id', string='Register Currency', store=True, readonly=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True,
        default=lambda self: self.env.company.currency_id.id)
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id', tracking=True)
    amount_register = fields.Monetary(
        string='Amount in Register Currency', compute='_compute_amount_register', store=False,
        currency_field='register_currency_id',
        help='The document amount converted into the register currency, using the rate '
             'for the document date. Not stored — reflects the current rate.')
    company_currency_id = fields.Many2one(
        related='company_id.currency_id', string='Company Currency', store=True, readonly=True)
    amount_company = fields.Monetary(
        string='Amount (Company)', compute='_compute_amount_company', store=False,
        currency_field='company_currency_id',
        help='The document amount converted into the company currency (for cross-register totals).')

    category_id = fields.Many2one('finance.category', string='Category', tracking=True)
    category_direction = fields.Selection(
        selection=[('income', 'Income'), ('expense', 'Expense')],
        compute='_compute_category_direction', string='Category Direction')
    detail_type = fields.Selection(related='category_id.detail_type', string='Detail Type')

    # Cascading detail fields (only one shown, per category.detail_type)
    expense_id = fields.Many2one('finance.expense', string='Expense Item')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    student_id = fields.Many2one('res.partner', string='Student', domain=[('is_student', '=', True)])
    partner_id = fields.Many2one('res.partner', string='Partner')

    payment_method_id = fields.Many2one(
        'finance.payment.method', string='Payment Method',
        default=lambda self: self.env['finance.payment.method'].search([], limit=1).id)
    note = fields.Text(string='Note')
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('confirmed', 'Confirmed'), ('cancelled', 'Cancelled')],
        string='Status', default='draft', required=True, tracking=True, copy=False)

    # ── Computes ──────────────────────────────────────────────────────────────

    @api.depends('move_type')
    def _compute_category_direction(self):
        for rec in self:
            rec.category_direction = 'income' if rec.move_type == 'cash_in' else 'expense'

    @api.depends('amount', 'currency_id', 'register_currency_id')
    def _compute_amount_register(self):
        for rec in self:
            if rec.amount and rec.currency_id and rec.register_currency_id:
                rec.amount_register = rec.currency_id.finance_convert(
                    rec.amount, rec.register_currency_id)
            else:
                rec.amount_register = 0.0

    @api.depends('amount', 'currency_id', 'company_currency_id')
    def _compute_amount_company(self):
        for rec in self:
            if rec.amount and rec.currency_id and rec.company_currency_id:
                rec.amount_company = rec.currency_id.finance_convert(
                    rec.amount, rec.company_currency_id)
            else:
                rec.amount_company = 0.0

    # ── Onchange ──────────────────────────────────────────────────────────────

    @api.onchange('register_id')
    def _onchange_register_id(self):
        if self.register_id:
            self.currency_id = self.register_id.currency_id

    @api.onchange('move_type')
    def _onchange_move_type(self):
        # category direction changed → drop a category that no longer matches
        if self.category_id and self.category_id.direction != self.category_direction:
            self.category_id = False

    @api.onchange('category_id')
    def _onchange_category_id(self):
        self.expense_id = False
        self.employee_id = False
        self.student_id = False
        self.partner_id = False

    # ── Constraints ───────────────────────────────────────────────────────────

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_('Amount must be greater than zero.'))

    # ── ORM ───────────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                code = 'finance.cash.in' if vals.get('move_type') == 'cash_in' else 'finance.cash.out'
                vals['name'] = self.env['ir.sequence'].next_by_code(code) or 'New'
        return super().create(vals_list)

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft documents can be confirmed.'))
            if rec.amount <= 0:
                raise UserError(_('Amount must be greater than zero.'))
            rec.state = 'confirmed'

    def action_draft(self):
        for rec in self:
            if rec.state == 'confirmed':
                rec.state = 'draft'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'
