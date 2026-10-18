# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResCurrency(models.Model):
    """Simplified rate management for the Finance module: a single editable
    `finance_rate` field — "1 company currency = X of this currency" (today's
    rate). Writing it creates/updates today's res.currency.rate line."""
    _inherit = 'res.currency'

    is_company_currency = fields.Boolean(
        string='Is Company Currency', compute='_compute_is_company_currency')
    rate_hint = fields.Char(compute='_compute_rate_hint', string=' ')
    finance_rate = fields.Float(
        string='Rate', digits=(12, 6),
        compute='_compute_finance_rate', inverse='_inverse_finance_rate',
        help="Today's rate: how many units of THIS currency equal 1 unit of the "
             "company currency. The company currency itself is always 1.")

    @api.depends_context('company')
    def _compute_is_company_currency(self):
        company_currency = self.env.company.currency_id
        for cur in self:
            cur.is_company_currency = (cur == company_currency)

    @api.depends_context('company')
    def _compute_rate_hint(self):
        name = self.env.company.currency_id.name or ''
        for cur in self:
            cur.rate_hint = f"1 {name} ="

    @api.depends('rate_ids.rate', 'rate_ids.name', 'rate_ids.company_id')
    @api.depends_context('company')
    def _compute_finance_rate(self):
        """Read the most recent rate line on/before today straight from the stored
        rate_ids — NOT from the SQL-computed `rate` field, which is not invalidated
        when we write a new rate line in the same transaction (caused the revert)."""
        today = fields.Date.context_today(self)
        company = self.env.company
        Rate = self.env['res.currency.rate'].sudo()
        for cur in self:
            if cur == company.currency_id:
                cur.finance_rate = 1.0
                continue
            line = Rate.search(
                [('currency_id', '=', cur.id),
                 ('name', '<=', today),
                 ('company_id', 'in', [company.id, False])],
                order='name desc, company_id desc', limit=1,
            )
            cur.finance_rate = line.rate if line else (cur.rate or 1.0)

    def finance_convert(self, amount, to_currency):
        """Convert `amount` from this currency to `to_currency` using the
        Finance `finance_rate` (today's rate shown on the Currencies screen).
        Deterministic — does not depend on Odoo's date/company rate resolution.
        finance_rate = units of a currency per 1 unit of the company currency."""
        if not amount or not to_currency:
            return 0.0
        if self == to_currency:
            return to_currency.round(amount)
        from_rate = self.finance_rate or 1.0
        to_rate = to_currency.finance_rate or 1.0
        if not from_rate:
            return 0.0
        return to_currency.round(amount * (to_rate / from_rate))

    def _inverse_finance_rate(self):
        Rate = self.env['res.currency.rate'].sudo()
        today = fields.Date.context_today(self)
        company = self.env.company
        for cur in self:
            if cur == company.currency_id:
                continue  # base currency is always 1
            value = cur.finance_rate or 0.0
            if value <= 0:
                continue
            line = Rate.search([
                ('currency_id', '=', cur.id),
                ('name', '=', today),
                ('company_id', '=', company.id),
            ], limit=1)
            if line:
                line.rate = value
            else:
                Rate.create({
                    'currency_id': cur.id,
                    'name': today,
                    'rate': value,
                    'company_id': company.id,
                })
