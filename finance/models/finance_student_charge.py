# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class FinanceStudentCharge(models.Model):
    """A debt / charge document for a student: the amount the student is expected
    to pay (set when an applicant becomes a paying student). Cash In payments
    reduce the remaining debt; this is the document shown first in the customer
    report, with cash moves below it."""
    _name = 'finance.student.charge'
    _description = 'Student Charge (Debt)'
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', default='New', readonly=True, copy=False, index=True)
    student_id = fields.Many2one('res.partner', string='Student', required=True, index=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True,
        default=lambda self: self.env.company.currency_id.id)
    amount = fields.Monetary(string='Amount to Pay', required=True, currency_field='currency_id')

    company_currency_id = fields.Many2one(
        related='company_id.currency_id', string='Company Currency', store=True, readonly=True)
    amount_company = fields.Monetary(
        string='Amount (Company)', compute='_compute_amount_company', store=False,
        currency_field='company_currency_id')

    source = fields.Selection(
        selection=[('trial', 'Trial Lesson'), ('manual', 'Manual')],
        string='Source', default='manual', readonly=True)
    trial_lesson_id = fields.Many2one('trail.lesson', string='Trial Lesson', readonly=True)
    note = fields.Text(string='Note')

    @api.depends('amount', 'currency_id', 'company_currency_id')
    def _compute_amount_company(self):
        for rec in self:
            if rec.amount and rec.currency_id and rec.company_currency_id:
                rec.amount_company = rec.currency_id.finance_convert(
                    rec.amount, rec.company_currency_id)
            else:
                rec.amount_company = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'finance.student.charge') or 'New'
        return super().create(vals_list)

    # ── Customer report ───────────────────────────────────────────────────────

    @api.model
    def get_customer_report(self, period='all', date_from=None, date_to=None,
                            partner_id=None, move_type=None):
        """Per customer (student/applicant) ledger for the selected period.

        Each customer's header row carries the **Opening Balance** (net debt
        before the period start), the period's **In** / **Out** totals and the
        **Remaining** balance (opening + period net). The detail rows below list
        every operation (charge / cash in / cash out) in the period, each showing
        only its In or Out value.

        All amounts are normalised to the company currency; the Currency column
        shows each document's own currency. Opening / totals / remaining always
        cover **all** operation types — the Type filter only narrows the visible
        detail rows. Filters mirror the operations report (period presets +
        From/To, plus customer and type).
        """
        company = self.env.company
        ccy = company.currency_id
        Partner = self.env['res.partner']
        Move = self.env['finance.cash.move']
        Register = self.env['finance.cash.register']
        Register._check_finance_access()

        cur, _prev, _label = Register._period_ranges(period, date_from, date_to)
        # _period_ranges may return ISO strings (e.g. 'between' passes the raw
        # filter values through); coerce to date for the Python comparisons below.
        d_from = fields.Date.to_date(cur[0])
        d_to = fields.Date.to_date(cur[1])

        def cfmt(val):
            return f"{val:,.2f} {ccy.symbol or ''}".strip()

        def num(val):
            return f"{val:,.2f}"

        base_pdomain = ['|', ('is_student', '=', True), ('is_applicant', '=', True)]
        all_partners = Partner.search(base_pdomain)
        data_partners = all_partners
        if partner_id:
            data_partners = all_partners.filtered(lambda p: p.id == partner_id)

        customers = []
        for p in data_partners:
            charges = self.search([('student_id', '=', p.id)])
            moves = Move.search([
                ('student_id', '=', p.id), ('state', '=', 'confirmed'),
            ])
            if not charges and not moves:
                continue

            # Opening balance: net debt strictly before the period start.
            opening = 0.0
            for ch in charges:
                if ch.date and ch.date < d_from:
                    opening += ch.amount_company
            for m in moves:
                if m.date and m.date < d_from:
                    opening += -m.amount_company if m.move_type == 'cash_in' else m.amount_company

            # Period operations (all types) → rows + In/Out totals + net change.
            raw = []
            total_in = 0.0
            total_out = 0.0
            charge_total = 0.0

            for ch in charges:
                if not (ch.date and d_from <= ch.date <= d_to):
                    continue
                charge_total += ch.amount_company
                raw.append({
                    'sort': (ch.date, 0, ch.id),
                    'type': 'charge', 'type_label': 'Debt',
                    'date': ch.date.strftime('%d.%m.%Y'),
                    'name': ch.name,
                    'currency': ch.currency_id.symbol or '',
                    'debtv': ch.amount_company, 'inv': 0.0, 'outv': 0.0,
                    'res_model': 'finance.student.charge', 'res_id': ch.id,
                })

            for m in moves:
                if not (m.date and d_from <= m.date <= d_to):
                    continue
                is_in = m.move_type == 'cash_in'
                amt = m.amount_company
                if is_in:
                    total_in += amt
                else:
                    total_out += amt
                raw.append({
                    'sort': (m.date, 1, m.id),
                    'type': 'cash_in' if is_in else 'cash_out',
                    'type_label': 'Cash In' if is_in else 'Cash Out',
                    'date': m.date.strftime('%d.%m.%Y'),
                    'name': m.name,
                    'currency': m.currency_id.symbol or '',
                    'debtv': 0.0,
                    'inv': amt if is_in else 0.0,
                    'outv': 0.0 if is_in else amt,
                    'res_model': 'finance.cash.move', 'res_id': m.id,
                })

            # Remaining = opening + (charges − cash in + cash out) over the period.
            remaining = opening + charge_total - total_in + total_out

            # Type filter narrows only the visible detail rows.
            display = raw
            if move_type:
                display = [r for r in raw if r['type'] == move_type]
            display.sort(key=lambda r: r['sort'])

            rows = [{
                'type': r['type'], 'type_label': r['type_label'],
                'date': r['date'], 'name': r['name'], 'currency': r['currency'],
                'debt_fmt': num(r['debtv']) if r['debtv'] else '',
                'in_fmt': num(r['inv']) if r['inv'] else '',
                'out_fmt': f"-{num(r['outv'])}" if r['outv'] else '',
                'res_model': r['res_model'], 'res_id': r['res_id'],
            } for r in display]

            # Nothing to show for this period (no rows, flat balance) → skip.
            if not rows and abs(opening) < 0.005 and abs(remaining) < 0.005:
                continue

            customers.append({
                'partner_id': p.id,
                'name': p.name,
                'is_student': p.is_student,
                'is_applicant': p.is_applicant,
                'opening': opening,
                'opening_fmt': cfmt(opening),
                'debt_fmt': cfmt(charge_total),
                'in_fmt': cfmt(total_in),
                'out_fmt': cfmt(total_out),
                'remaining': remaining,
                'remaining_fmt': cfmt(remaining),
                'rows': rows,
            })

        # most debt first
        customers.sort(key=lambda c: -c['remaining'])
        return {
            'customers': customers,
            'currency': ccy.symbol or '',
            'partner_options': [{'value': p.id, 'label': p.name} for p in all_partners],
        }
