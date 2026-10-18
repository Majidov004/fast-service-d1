# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class TrailLessonCompleteWizardFinance(models.TransientModel):
    """Finance extension of the trial-completion wizard. Lives here (not in
    trail_lesson) because referencing finance models from trail_lesson would be a
    circular dependency. When the applicant converts (joining + now), it creates
    a Student Charge (debt) for the total amount to pay and an auto Cash In for
    the initial payment."""
    _inherit = 'trail.lesson.complete.wizard'

    register_id = fields.Many2one(
        'finance.cash.register', string='Cash Register',
        default=lambda self: self._default_finance_register())
    total_payment_amount = fields.Float(
        string='Total Amount to Pay', digits=(10, 2),
        help='The full amount the student is expected to pay. A debt document '
             'is created for this amount; the Payment Amount is the initial '
             'cash received.')
    promise_due_date = fields.Date(
        string='Next Payment Date',
        help='If the student will pay the rest later, set the date here. A reminder '
             'is scheduled for that day.')

    @api.model
    def _default_finance_register(self):
        param = self.env['ir.config_parameter'].sudo().get_param('finance.default_register_id')
        if param:
            reg = self.env['finance.cash.register'].browse(int(param))
            if reg.exists():
                return reg.id
        return self.env['finance.cash.register'].search([], limit=1).id

    @api.model
    def _finance_student_payment_category(self):
        param = self.env['ir.config_parameter'].sudo().get_param('finance.student_payment_category_id')
        if param:
            cat = self.env['finance.category'].browse(int(param))
            if cat.exists():
                return cat
        cat = self.env.ref('finance.cat_student_payment', raise_if_not_found=False)
        if cat:
            return cat
        return self.env['finance.category'].search([('direction', '=', 'income')], limit=1)

    def action_confirm(self):
        self.ensure_one()
        # Full payment: the student pays the whole amount now, so the "paying now"
        # amount equals the total. We hide payment_amount in the view for Full and
        # mirror it here BEFORE super() runs (the base wizard requires a positive
        # payment_amount on joining+now, and this also drives the auto Cash In).
        if self.payment_type == 'full' and self.total_payment_amount:
            self.payment_amount = self.total_payment_amount
        res = super().action_confirm()
        # Push financial data to finance whenever the student is joining, OR has
        # already paid part of the fee, OR owes a total, OR promised a future
        # payment — not only on the "joining + now" full-conversion path. This
        # captures partial/deposit payments made by students who join later.
        if (self.decision == 'joining'
                or self.payment_amount
                or self.total_payment_amount
                or self.promise_due_date):
            self._finance_create_documents()
        return res

    def _finance_create_documents(self):
        partner = self.lesson_id.student_id
        if not partner:
            return
        register = self.register_id or self.env['finance.cash.register'].search([], limit=1)
        if not register:
            return
        currency = register.currency_id
        lesson_ref = self.lesson_id.name or ''

        # ── Debt document for the total amount to pay ──
        charge = self.env['finance.student.charge']
        total = self.total_payment_amount or 0.0
        if total > 0:
            charge = self.env['finance.student.charge'].create({
                'student_id': partner.id,
                'amount': total,
                'currency_id': currency.id,
                'date': fields.Date.context_today(self),
                'source': 'trial',
                'trial_lesson_id': self.lesson_id.id,
                'note': _('Auto-created when the applicant became a student (trial %s).') % lesson_ref,
            })

        # ── Auto Cash In for the initial payment ──
        paid = self.payment_amount or 0.0
        if paid > 0:
            category = self._finance_student_payment_category()
            move = self.env['finance.cash.move'].create({
                'move_type': 'cash_in',
                'register_id': register.id,
                'currency_id': currency.id,
                'amount': paid,
                'category_id': category.id if category else False,
                'student_id': partner.id,
                'date': fields.Date.context_today(self),
                'note': _('Auto-created from applicant payment (trial %s).') % lesson_ref,
            })
            move.action_confirm()

        # ── Future payment promise (reminder) ──
        if self.promise_due_date:
            self.env['finance.payment.promise'].create({
                'student_id': partner.id,
                'currency_id': currency.id,
                'register_id': register.id,
                'charge_id': charge.id if charge else False,
                'responsible_user_id': self.env.user.id,
                'due_date': self.promise_due_date,
                'note': _('Rest of the trial payment (%s).') % (lesson_ref or ''),
            })
