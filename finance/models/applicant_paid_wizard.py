# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class FinanceApplicantPaidWizard(models.TransientModel):
    """Dialog opened by the applicant's "Paid" button. Shows the customer's
    current outstanding debt, lets the operator optionally create a new debt
    (Student Charge) and/or register an incoming payment (Cash In), then
    converts the applicant into a paying student.

    Lives in `finance` (not contact_customization) because it references finance
    models; finance already depends on contact_customization, so the reverse
    reference here is safe and avoids a circular dependency."""
    _name = 'finance.applicant.paid.wizard'
    _description = 'Convert Applicant to Paid Student'

    partner_id = fields.Many2one(
        'res.partner', string='Applicant', required=True, readonly=True)

    payment_type = fields.Selection(
        selection=[('full', 'Full Payment'), ('deposit', 'Deposit')],
        string='Payment Type',
        help='Full Payment: the student clears the whole outstanding debt now. '
             'Deposit: the student pays part now and the rest later.')

    register_id = fields.Many2one(
        'finance.cash.register', string='Cash Register',
        default=lambda self: self._default_register())
    register_currency_id = fields.Many2one(
        related='register_id.currency_id', string='Register Currency', readonly=True)

    company_currency_id = fields.Many2one(
        'res.currency', string='Company Currency', readonly=True,
        default=lambda self: self.env.company.currency_id.id)
    current_debt = fields.Monetary(
        string='Current Debt', compute='_compute_current_debt',
        currency_field='company_currency_id',
        help='The customer\'s outstanding debt so far: all charges minus '
             'confirmed Cash In plus confirmed Cash Out (company currency).')

    create_charge = fields.Boolean(
        string='Create New Debt', compute='_compute_create_charge',
        readonly=False, store=True,
        help='Tick to also record a new debt (Student Charge) for the amount '
             'below — e.g. when the student has no debt yet. Auto-ticked when '
             'there is no outstanding debt.')
    charge_amount = fields.Monetary(
        string='New Debt Amount', currency_field='register_currency_id')
    total_due = fields.Monetary(
        string='Total Due', compute='_compute_total_due',
        currency_field='company_currency_id',
        help='Current debt plus the new debt being created — the amount a Full '
             'Payment must cover.')

    paid_now = fields.Monetary(
        string='Paid Now (Cash In)', currency_field='register_currency_id',
        help='Amount the student pays now. For Full Payment it is pre-filled with '
             'the total due; reducing it below the total switches to Deposit.')

    category_id = fields.Many2one(
        'finance.category', string='Payment Category',
        domain=[('direction', '=', 'income')],
        default=lambda self: self._default_category())
    payment_method_id = fields.Many2one(
        'finance.payment.method', string='Payment Method',
        default=lambda self: self.env['finance.payment.method'].search([], limit=1).id)
    promise_due_date = fields.Date(
        string='Next Payment Date',
        help='If the student will pay the rest later, set the date here. A reminder '
             'is scheduled for that day.')
    note = fields.Text(string='Note')

    # ── Defaults ──────────────────────────────────────────────────────────────

    @api.model
    def _default_register(self):
        param = self.env['ir.config_parameter'].sudo().get_param('finance.default_register_id')
        if param:
            reg = self.env['finance.cash.register'].browse(int(param))
            if reg.exists():
                return reg.id
        return self.env['finance.cash.register'].search([], limit=1).id

    @api.model
    def _default_category(self):
        param = self.env['ir.config_parameter'].sudo().get_param('finance.student_payment_category_id')
        if param:
            cat = self.env['finance.category'].browse(int(param))
            if cat.exists():
                return cat.id
        cat = self.env.ref('finance.cat_student_payment', raise_if_not_found=False)
        if cat:
            return cat.id
        return self.env['finance.category'].search([('direction', '=', 'income')], limit=1).id

    # ── Computes ──────────────────────────────────────────────────────────────

    @api.depends('partner_id')
    def _compute_current_debt(self):
        Charge = self.env['finance.student.charge']
        Move = self.env['finance.cash.move']
        for wiz in self:
            partner = wiz.partner_id
            if not partner:
                wiz.current_debt = 0.0
                continue
            charged = sum(Charge.search(
                [('student_id', '=', partner.id)]).mapped('amount_company'))
            moves = Move.search([
                ('student_id', '=', partner.id), ('state', '=', 'confirmed')])
            paid = sum(m.amount_company for m in moves if m.move_type == 'cash_in')
            refund = sum(m.amount_company for m in moves if m.move_type == 'cash_out')
            wiz.current_debt = charged - paid + refund

    @api.depends('current_debt')
    def _compute_create_charge(self):
        # Suggest creating a debt only when none exists yet.
        for wiz in self:
            wiz.create_charge = wiz.current_debt <= 0

    @api.depends('current_debt', 'create_charge', 'charge_amount')
    def _compute_total_due(self):
        for wiz in self:
            extra = wiz.charge_amount if wiz.create_charge else 0.0
            wiz.total_due = wiz.current_debt + extra

    # ── Onchange: Payment Type ↔ Paid Now ─────────────────────────────────────

    @api.onchange('payment_type', 'create_charge', 'charge_amount')
    def _onchange_full_prefill(self):
        """Full Payment pre-fills the whole amount due (current debt + any new
        debt being created) into 'Paid Now'."""
        if self.payment_type == 'full':
            self.paid_now = self.total_due

    @api.onchange('paid_now')
    def _onchange_paid_now(self):
        """If the operator pays less than the total due under Full Payment, it is
        no longer a full payment — switch to Deposit so the promise fields show."""
        if self.payment_type == 'full' and self.paid_now < self.total_due:
            self.payment_type = 'deposit'

    # ── Confirm ───────────────────────────────────────────────────────────────

    def action_confirm(self):
        self.ensure_one()
        partner = self.partner_id
        register = self.register_id
        currency = register.currency_id if register else self.company_currency_id

        # ── Optional new debt (Student Charge) ──
        charge = self.env['finance.student.charge']
        if self.create_charge and self.charge_amount > 0:
            charge = self.env['finance.student.charge'].create({
                'student_id': partner.id,
                'amount': self.charge_amount,
                'currency_id': currency.id,
                'date': fields.Date.context_today(self),
                'source': 'manual',
                'note': self.note or _('Created when the applicant became a student.'),
            })

        # ── Incoming payment (Cash In) ──
        if self.paid_now > 0:
            if not register:
                raise UserError(_('Please select a Cash Register to register the payment.'))
            move = self.env['finance.cash.move'].create({
                'move_type': 'cash_in',
                'register_id': register.id,
                'currency_id': currency.id,
                'amount': self.paid_now,
                'category_id': self.category_id.id if self.category_id else False,
                'payment_method_id': self.payment_method_id.id if self.payment_method_id else False,
                'student_id': partner.id,
                'date': fields.Date.context_today(self),
                'note': self.note or _('Payment registered when the applicant became a student.'),
            })
            move.action_confirm()

        # ── Future payment promise (reminder) — Deposit with a date ──
        if self.promise_due_date:
            self.env['finance.payment.promise'].create({
                'student_id': partner.id,
                'currency_id': currency.id,
                'register_id': register.id if register else False,
                'charge_id': charge.id if charge else False,
                'responsible_user_id': self.env.user.id,
                'due_date': self.promise_due_date,
                'note': self.note,
            })

        # ── Convert applicant → student (skip re-opening this wizard) ──
        partner.with_context(skip_finance_wizard=True).action_set_paid()

        return {'type': 'ir.actions.act_window_close'}
