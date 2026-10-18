# -*- coding: utf-8 -*-
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import AccessError


class FinanceCashRegister(models.Model):
    """A cash register / account. Holds its own currency. The current balance is
    computed from confirmed cash moves and transfers (never shown on documents,
    only on the dashboard)."""
    _name = 'finance.cash.register'
    _description = 'Cash Register'
    _order = 'name'

    name = fields.Char(string='Cash Register', required=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True,
        default=lambda self: self.env.company.currency_id.id,
    )
    responsible_user_id = fields.Many2one('res.users', string='Responsible')
    active = fields.Boolean(default=True)
    note = fields.Text()
    balance = fields.Monetary(
        string='Current Balance', compute='_compute_balance',
        currency_field='currency_id',
    )

    # ── Balance ───────────────────────────────────────────────────────────────

    def _compute_balance(self):
        Move = self.env['finance.cash.move']
        Transfer = self.env['finance.transfer']
        for reg in self:
            ins = sum(Move.search([
                ('register_id', '=', reg.id),
                ('move_type', '=', 'cash_in'),
                ('state', '=', 'confirmed'),
            ]).mapped('amount_register'))
            outs = sum(Move.search([
                ('register_id', '=', reg.id),
                ('move_type', '=', 'cash_out'),
                ('state', '=', 'confirmed'),
            ]).mapped('amount_register'))
            t_out = sum(Transfer.search([
                ('from_register_id', '=', reg.id),
                ('state', '=', 'confirmed'),
            ]).mapped('amount'))
            t_in = sum(Transfer.search([
                ('to_register_id', '=', reg.id),
                ('state', '=', 'confirmed'),
            ]).mapped('amount_to'))
            reg.balance = ins - outs - t_out + t_in

    # ── Dashboard helpers ─────────────────────────────────────────────────────

    def _period_ranges(self, period, date_from=None, date_to=None):
        """Return ((cur_from, cur_to), prev_or_None, prev_label).

        prev is None for 'between' and 'all' (no meaningful baseline), which makes
        the trend percentage hidden in the UI."""
        today = fields.Date.context_today(self)
        if period == 'day':
            cur = (today, today)
            prev = (today - timedelta(days=1), today - timedelta(days=1))
            prev_label = 'yesterday'
        elif period == 'week':
            start = today - timedelta(days=today.weekday())
            cur = (start, start + timedelta(days=6))
            pstart = start - timedelta(days=7)
            prev = (pstart, pstart + timedelta(days=6))
            prev_label = 'last week'
        elif period in ('last_3m', 'last_6m', 'last_1y'):
            if period == 'last_3m':
                cur_from = today - relativedelta(months=3)
                prev_label = 'previous 3 months'
            elif period == 'last_6m':
                cur_from = today - relativedelta(months=6)
                prev_label = 'previous 6 months'
            else:
                cur_from = today - relativedelta(years=1)
                prev_label = 'previous year'
            cur = (cur_from, today)
            # equal-length window immediately before
            length = (today - cur_from).days
            prev_to = cur_from - timedelta(days=1)
            prev = (prev_to - timedelta(days=length), prev_to)
        elif period == 'between':
            cur = (date_from or today, date_to or today)
            prev = None
            prev_label = ''
        elif period == 'all':
            cur = (fields.Date.to_date('1970-01-01'), today)
            prev = None
            prev_label = ''
        else:  # month (default)
            start = today.replace(day=1)
            cur = (start, start + relativedelta(months=1) - timedelta(days=1))
            pstart = start - relativedelta(months=1)
            prev = (pstart, start - timedelta(days=1))
            prev_label = 'last month'
        return cur, prev, prev_label

    def _sum_io(self, date_from, date_to):
        """Sum confirmed in/out (in this register's currency) within a date range."""
        self.ensure_one()
        Move = self.env['finance.cash.move']
        base = [
            ('register_id', '=', self.id),
            ('state', '=', 'confirmed'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]
        money_in = sum(Move.search(base + [('move_type', '=', 'cash_in')]).mapped('amount_register'))
        money_out = sum(Move.search(base + [('move_type', '=', 'cash_out')]).mapped('amount_register'))
        return money_in, money_out

    @staticmethod
    def _pct(cur, prev):
        if not prev:
            return {'has': False, 'value': 0.0, 'dir': 'flat'}
        diff = (cur - prev) / prev * 100.0
        direction = 'up' if diff > 0 else ('down' if diff < 0 else 'flat')
        return {'has': True, 'value': round(abs(diff), 1), 'dir': direction}

    def _card_payload(self, period, date_from=None, date_to=None):
        self.ensure_one()
        cur, prev, prev_label = self._period_ranges(period, date_from, date_to)
        cin, cout = self._sum_io(cur[0], cur[1])
        if prev:
            pin, pout = self._sum_io(prev[0], prev[1])
        else:
            pin, pout = 0.0, 0.0
        sym = self.currency_id.symbol or ''

        def fmt(val):
            return f"{val:,.2f} {sym}".strip()

        return {
            'id': self.id,
            'name': self.name,
            'currency': sym,
            'balance': self.balance,
            'balance_fmt': fmt(self.balance),
            'period': period,
            'prev_label': prev_label,
            'money_in': cin,
            'money_in_fmt': fmt(cin),
            'money_out': cout,
            'money_out_fmt': fmt(cout),
            'in_pct': self._pct(cin, pin),
            'out_pct': self._pct(cout, pout),
        }

    @api.model
    def _check_finance_access(self):
        """Finance dashboard/report data metodları üçün giriş yoxlaması. Yalnız
        'Finance Dashboard & Reports' qrupu və ya admin (menyu gizli olsa da
        endpoint qorunur)."""
        if self.env.user.has_group('base.group_system') or \
                self.env.user.has_group('finance.group_finance_user'):
            return
        raise AccessError(_("Bu məlumatı görmək üçün icazəniz yoxdur."))

    @api.model
    def get_dashboard(self, period='month', date_from=None, date_to=None):
        """All active registers as dashboard cards for the given period."""
        self._check_finance_access()
        return [reg._card_payload(period, date_from, date_to) for reg in self.search([])]

    def get_card_data(self, period='month', date_from=None, date_to=None):
        """Single register card data — used when a card switches its period."""
        self._check_finance_access()
        self.ensure_one()
        return self._card_payload(period, date_from, date_to)

    # ── Detailed operations report (running balance per register) ─────────────

    def _balance_before(self, date):
        """Confirmed balance of this register strictly before `date`
        (register currency). Used as the opening balance of the report period."""
        self.ensure_one()
        Move = self.env['finance.cash.move']
        Transfer = self.env['finance.transfer']
        ins = sum(Move.search([
            ('register_id', '=', self.id), ('move_type', '=', 'cash_in'),
            ('state', '=', 'confirmed'), ('date', '<', date),
        ]).mapped('amount_register'))
        outs = sum(Move.search([
            ('register_id', '=', self.id), ('move_type', '=', 'cash_out'),
            ('state', '=', 'confirmed'), ('date', '<', date),
        ]).mapped('amount_register'))
        t_out = sum(Transfer.search([
            ('from_register_id', '=', self.id), ('state', '=', 'confirmed'),
            ('date', '<', date),
        ]).mapped('amount'))
        t_in = sum(Transfer.search([
            ('to_register_id', '=', self.id), ('state', '=', 'confirmed'),
            ('date', '<', date),
        ]).mapped('amount_to'))
        return ins - outs - t_out + t_in

    @api.model
    def get_operations_report(self, period='month', date_from=None, date_to=None,
                              register_id=None, category_id=None):
        """Per-register ledger for the period: confirmed cash moves + transfers,
        ordered by date, each row carrying the running balance (register currency)
        and the category's detail (expense item / employee / student / partner).
        Optionally filtered to a single register and/or category (a category
        filter excludes transfers, which carry no category)."""
        self._check_finance_access()
        cur, _prev, _label = self._period_ranges(period, date_from, date_to)
        Move = self.env['finance.cash.move']
        Transfer = self.env['finance.transfer']

        all_registers = self.search([])
        registers = all_registers
        if register_id:
            registers = registers.filtered(lambda r: r.id == register_id)

        def move_detail(m):
            if m.detail_type == 'expense':
                return m.expense_id.name or ''
            if m.detail_type == 'employee':
                return m.employee_id.name or ''
            if m.detail_type == 'student':
                return m.student_id.name or ''
            if m.detail_type == 'partner':
                return m.partner_id.name or ''
            return ''

        result = []
        for reg in registers:
            sym = reg.currency_id.symbol or ''

            def rfmt(val):
                return f"{val:,.2f} {sym}".strip()

            opening = reg._balance_before(cur[0])
            raw = []

            move_domain = [
                ('register_id', '=', reg.id), ('state', '=', 'confirmed'),
                ('date', '>=', cur[0]), ('date', '<=', cur[1]),
            ]
            if category_id:
                move_domain.append(('category_id', '=', category_id))
            for m in Move.search(move_domain):
                is_in = m.move_type == 'cash_in'
                raw.append({
                    'date': m.date, 'sort': (m.date, m.id),
                    'name': m.name,
                    'category': m.category_id.name or 'Uncategorized',
                    'detail': move_detail(m),
                    'doc_currency': m.currency_id.symbol or '',
                    'inv': m.amount_register if is_in else 0.0,
                    'outv': 0.0 if is_in else m.amount_register,
                    'res_model': 'finance.cash.move', 'res_id': m.id,
                })

            if not category_id:
                for t in Transfer.search([
                    ('from_register_id', '=', reg.id), ('state', '=', 'confirmed'),
                    ('date', '>=', cur[0]), ('date', '<=', cur[1]),
                ]):
                    raw.append({
                        'date': t.date, 'sort': (t.date, t.id),
                        'name': t.name, 'category': 'Transfer →',
                        'detail': t.to_register_id.name or '',
                        'doc_currency': sym, 'inv': 0.0, 'outv': t.amount,
                        'res_model': 'finance.transfer', 'res_id': t.id,
                    })
                for t in Transfer.search([
                    ('to_register_id', '=', reg.id), ('state', '=', 'confirmed'),
                    ('date', '>=', cur[0]), ('date', '<=', cur[1]),
                ]):
                    raw.append({
                        'date': t.date, 'sort': (t.date, t.id),
                        'name': t.name, 'category': 'Transfer ←',
                        'detail': t.from_register_id.name or '',
                        'doc_currency': sym, 'inv': t.amount_to, 'outv': 0.0,
                        'res_model': 'finance.transfer', 'res_id': t.id,
                    })

            raw.sort(key=lambda r: r['sort'])
            running = opening
            rows = []
            for r in raw:
                running += r['inv'] - r['outv']
                rows.append({
                    'date': r['date'].strftime('%d.%m.%Y') if r['date'] else '',
                    'name': r['name'],
                    'category': r['category'],
                    'detail': r['detail'],
                    'doc_currency': r['doc_currency'],
                    'in_fmt': rfmt(r['inv']) if r['inv'] else '',
                    'out_fmt': rfmt(r['outv']) if r['outv'] else '',
                    'balance_fmt': rfmt(running),
                    'res_model': r['res_model'],
                    'res_id': r['res_id'],
                })

            result.append({
                'register_id': reg.id,
                'register_name': reg.name,
                'currency': sym,
                'opening_fmt': rfmt(opening),
                'closing_fmt': rfmt(running),
                'rows': rows,
                'has_data': bool(rows),
            })

        return {
            'registers': result,
            'register_options': [{'value': r.id, 'label': r.name} for r in all_registers],
            'category_options': [
                {'value': c.id, 'label': c.name}
                for c in self.env['finance.category'].search([])
            ],
        }

    # ── Overview (KPI + categories per register + recent) ─────────────────────

    @api.model
    def get_overview(self, period='month', date_from=None, date_to=None):
        """KPI strip + per-register category breakdown + recent moves.
        KPI cross-register figures are in the company currency; the per-register
        category amounts are in each register's own currency."""
        self._check_finance_access()
        company = self.env.company
        ccy = company.currency_id
        today = fields.Date.context_today(self)
        Move = self.env['finance.cash.move']
        cur, _prev, prev_label = self._period_ranges(period, date_from, date_to)

        def fmt(val):
            return f"{val:,.2f} {ccy.symbol or ''}".strip()

        # ── KPI ──
        total_balance = 0.0
        for reg in self.search([]):
            bal = reg.balance
            if bal and reg.currency_id != ccy:
                bal = reg.currency_id._convert(bal, ccy, company, today)
            total_balance += bal

        cur_moves = Move.search([
            ('state', '=', 'confirmed'),
            ('date', '>=', cur[0]), ('date', '<=', cur[1]),
        ])
        total_in = sum(cur_moves.filtered(lambda m: m.move_type == 'cash_in').mapped('amount_company'))
        total_out = sum(cur_moves.filtered(lambda m: m.move_type == 'cash_out').mapped('amount_company'))
        net = total_in - total_out
        kpi = {
            'total_balance': fmt(total_balance),
            'total_in': fmt(total_in),
            'total_out': fmt(total_out),
            'net': fmt(net),
            'net_positive': net >= 0,
            'draft_count': Move.search_count([('state', '=', 'draft')]),
        }

        # ── Categories per register (current period, register currency) ──
        # Table form: each category has its own In / Out amount + a Total row.
        categories_by_register = []
        for reg in self.search([]):
            rmoves = cur_moves.filtered(lambda m: m.register_id.id == reg.id)
            sym = reg.currency_id.symbol or ''

            def rfmt(val):
                return f"{val:,.2f} {sym}".strip()

            cats = {}
            for m in rmoves:
                cid = m.category_id.id or 0
                c = cats.setdefault(cid, {
                    'name': m.category_id.name or 'Uncategorized',
                    'in': 0.0, 'out': 0.0,
                })
                if m.move_type == 'cash_in':
                    c['in'] += m.amount_register
                else:
                    c['out'] += m.amount_register
            tin = sum(c['in'] for c in cats.values())
            tout = sum(c['out'] for c in cats.values())
            items = sorted([
                {
                    'id': cid,
                    'name': c['name'],
                    'in_fmt': rfmt(c['in']) if c['in'] else '',
                    'out_fmt': rfmt(c['out']) if c['out'] else '',
                } for cid, c in cats.items()
            ], key=lambda x: x['name'])
            categories_by_register.append({
                'register_id': reg.id,
                'register_name': reg.name,
                'has_data': bool(items),
                'total_in_fmt': rfmt(tin),
                'total_out_fmt': rfmt(tout),
                'items': items,
            })

        # ── Recent moves ──
        recent = []
        for m in Move.search([], limit=10):
            recent.append({
                'id': m.id,
                'name': m.name,
                'date': m.date.strftime('%d.%m.%Y') if m.date else '',
                'register': m.register_id.name or '',
                'category': m.category_id.name or '',
                'move_type': m.move_type,
                'amount_fmt': f"{m.amount:,.2f} {m.currency_id.symbol or ''}".strip(),
                'state': m.state,
            })

        return {
            'currency': ccy.symbol or '',
            'period': period,
            'prev_label': prev_label,
            'kpi': kpi,
            'categories_by_register': categories_by_register,
            'recent': recent,
        }
