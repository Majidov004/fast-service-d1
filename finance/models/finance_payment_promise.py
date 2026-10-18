# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class FinancePaymentPromise(models.Model):
    """A promise-to-pay: the student commits to pay a given amount on a future
    date (an installment). Each promise schedules a reminder activity for the
    responsible user on its due date, and a daily cron posts an active chatter
    message when the due date arrives. A promise is fulfilled by registering a
    Cash In, which marks it paid and closes its activity."""
    _name = 'finance.payment.promise'
    _description = 'Payment Promise (Installment)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'due_date, id'

    name = fields.Char(string='Reference', default='New', readonly=True, copy=False, index=True)
    student_id = fields.Many2one(
        'res.partner', string='Student', required=True, index=True, tracking=True)
    date = fields.Date(string='Promise Date', default=fields.Date.context_today, tracking=True)
    due_date = fields.Date(string='Due Date', required=True, tracking=True)

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True,
        default=lambda self: self.env.company.currency_id.id)
    amount = fields.Monetary(string='Promised Amount', currency_field='currency_id', tracking=True,
                             help='Optional — the expected amount. Set it before registering the payment.')

    company_currency_id = fields.Many2one(
        related='company_id.currency_id', string='Company Currency', store=True, readonly=True)
    amount_company = fields.Monetary(
        string='Amount (Company)', compute='_compute_amount_company', store=False,
        currency_field='company_currency_id')

    register_id = fields.Many2one('finance.cash.register', string='Cash Register')
    charge_id = fields.Many2one('finance.student.charge', string='Related Debt', ondelete='set null')
    responsible_user_id = fields.Many2one(
        'res.users', string='Responsible', default=lambda self: self.env.user, tracking=True,
        help='User who receives the reminder activity and message when the promise is due.')
    cash_move_id = fields.Many2one(
        'finance.cash.move', string='Payment', readonly=True, copy=False,
        help='The Cash In document created when this promise was fulfilled.')
    reminder_sent = fields.Boolean(string='Reminder Sent', default=False, copy=False)

    state = fields.Selection(
        selection=[('pending', 'Pending'), ('paid', 'Paid'), ('cancelled', 'Cancelled')],
        string='Status', default='pending', required=True, tracking=True, copy=False)
    note = fields.Text(string='Note')

    # ── Computes ──────────────────────────────────────────────────────────────

    @api.depends('amount', 'currency_id', 'company_currency_id')
    def _compute_amount_company(self):
        for rec in self:
            if rec.amount and rec.currency_id and rec.company_currency_id:
                rec.amount_company = rec.currency_id.finance_convert(
                    rec.amount, rec.company_currency_id)
            else:
                rec.amount_company = 0.0

    # ── ORM ───────────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'finance.payment.promise') or 'New'
        promises = super().create(vals_list)
        promises._schedule_reminder()
        return promises

    # ── Reminder activity ──────────────────────────────────────────────────────

    def _schedule_reminder(self):
        """Schedule a To-Do activity for the responsible user on the due date."""
        for rec in self:
            if rec.state != 'pending' or not rec.due_date:
                continue
            user = rec.responsible_user_id or self.env.user
            if rec.amount:
                note = _('Promised payment of %(amount)s %(currency)s is due. Please collect it.') % {
                    'amount': '{:,.2f}'.format(rec.amount),
                    'currency': rec.currency_id.symbol or '',
                }
            else:
                note = _('A promised payment is due. Please collect it.')
            rec.activity_schedule(
                'mail.mail_activity_data_todo',
                date_deadline=rec.due_date,
                summary=_('Collect payment from %s') % (rec.student_id.name or ''),
                note=note,
                user_id=user.id,
            )

    # ── Actions ───────────────────────────────────────────────────────────────

    @api.model
    def _payment_category(self):
        param = self.env['ir.config_parameter'].sudo().get_param('finance.student_payment_category_id')
        if param:
            cat = self.env['finance.category'].browse(int(param))
            if cat.exists():
                return cat
        cat = self.env.ref('finance.cat_student_payment', raise_if_not_found=False)
        if cat:
            return cat
        return self.env['finance.category'].search([('direction', '=', 'income')], limit=1)

    def action_register_payment(self):
        """Fulfill the promise: create a confirmed Cash In and mark it paid."""
        for rec in self:
            if rec.state != 'pending':
                raise UserError(_('Only pending promises can be paid.'))
            if rec.amount <= 0:
                raise UserError(_('Please set the Promised Amount before registering the payment.'))
            register = rec.register_id or self.env['finance.cash.register'].search([], limit=1)
            if not register:
                raise UserError(_('No cash register available to register the payment.'))
            category = rec._payment_category()
            move = self.env['finance.cash.move'].create({
                'move_type': 'cash_in',
                'register_id': register.id,
                'currency_id': rec.currency_id.id,
                'amount': rec.amount,
                'category_id': category.id if category else False,
                'student_id': rec.student_id.id,
                'date': fields.Date.context_today(rec),
                'note': _('Payment for promise %s.') % rec.name,
            })
            move.action_confirm()
            rec.cash_move_id = move.id
            rec.state = 'paid'
            rec.activity_ids.action_done()
            rec.message_post(body=_('Promise fulfilled — Cash In %s registered.') % move.name)
        return True

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'
            rec.activity_ids.unlink()

    def action_reset_pending(self):
        for rec in self:
            if rec.state == 'cancelled':
                rec.state = 'pending'
                rec.reminder_sent = False
                rec._schedule_reminder()

    # ── Cron ──────────────────────────────────────────────────────────────────

    @api.model
    def _cron_payment_promise_reminders(self):
        """Daily: for pending promises whose due date has arrived (or passed) and
        that have not been reminded yet, post a chatter message tagging the
        responsible user, then flag them so the message is sent only once."""
        today = fields.Date.context_today(self)
        promises = self.search([
            ('state', '=', 'pending'),
            ('due_date', '<=', today),
            ('reminder_sent', '=', False),
        ])
        for rec in promises:
            user = rec.responsible_user_id or self.env.user
            partner = user.partner_id
            amount_txt = ''
            if rec.amount:
                amount_txt = ' %s %s' % ('{:,.2f}'.format(rec.amount), rec.currency_id.symbol or '')
            body = _(
                '⚠️ Payment promise due: collect%(amount)s from %(student)s (due %(due)s).'
            ) % {
                'amount': amount_txt,
                'student': rec.student_id.name or '',
                'due': rec.due_date.strftime('%d.%m.%Y') if rec.due_date else '',
            }
            rec.message_post(
                body=body,
                partner_ids=partner.ids if partner else [],
            )
            rec.reminder_sent = True
        return True
