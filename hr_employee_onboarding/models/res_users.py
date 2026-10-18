# -*- coding: utf-8 -*-
import secrets
import string
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResUsers(models.Model):
    _inherit = 'res.users'

    onboarding_done = fields.Boolean(
        string='Onboarding Done',
        default=False,
        help='Set to True after employee completes their profile.',
    )

    def _generate_password(self, length=10):
        """Generate a random readable password."""
        chars = string.ascii_letters + string.digits
        return ''.join(secrets.choice(chars) for _ in range(length))

    def action_send_onboarding_invite(self):
        self.ensure_one()

        if not self.email:
            raise UserError(_('This user has no email address. Please add one first.'))

        employee = self.env['hr.employee'].search(
            [('user_id', '=', self.id)], limit=1
        )
        if not employee:
            raise UserError(_(
                'No employee record linked to this user. '
                'Please create an employee and link this user first.'
            ))

        # Generate & set password
        password = self._generate_password()
        self.sudo().write({'password': password})

        # Create a dedicated action pointing to employee form
        action = self.env['ir.actions.act_window'].sudo().create({
            'name': _('Complete My Profile'),
            'res_model': 'hr.employee',
            'res_id': employee.id,
            'view_mode': 'form',
            'target': 'current',
        })
        self.sudo().write({'action_id': action.id, 'onboarding_done': False})

        # Build login URL
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        login_url = '%s/web/login' % base_url

        emp_name = employee.name
        user_login = self.login
        user_email = self.email
        from_email = (
            self.env.user.email
            or self.env['ir.config_parameter'].sudo().get_param('mail.default.from')
            or 'noreply@example.com'
        )

        body = (
            '<div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;'
            'border:1px solid #e0e0e0;border-radius:8px;overflow:hidden;">'

            '<div style="background-color:#875A7B;padding:30px;text-align:center;">'
            '<h1 style="color:#ffffff;margin:0;font-size:24px;">Welcome to Odoo &#127881;</h1>'
            '</div>'

            '<div style="padding:30px;background:#ffffff;">'
            '<p style="font-size:16px;">Salam <strong>' + emp_name + '</strong>,</p>'
            '<p>Odoo hesab&#305;n&#305;z haz&#305;rd&#305;r. A&#351;a&#287;&#305;dak&#305; '
            'm&#601;lumatlarla sistem&#601; daxil ola bil&#601;rsiniz:</p>'

            '<table style="width:100%;border-collapse:collapse;margin:20px 0;">'
            '<tr>'
            '<td style="padding:10px;background:#f9f9f9;border:1px solid #e0e0e0;'
            'font-weight:bold;width:140px;">&#128279; Link</td>'
            '<td style="padding:10px;border:1px solid #e0e0e0;">'
            '<a href="' + login_url + '" style="color:#875A7B;">' + login_url + '</a>'
            '</td>'
            '</tr>'
            '<tr>'
            '<td style="padding:10px;background:#f9f9f9;border:1px solid #e0e0e0;'
            'font-weight:bold;">&#128100; İstifadəçi adı</td>'
            '<td style="padding:10px;border:1px solid #e0e0e0;">' + user_login + '</td>'
            '</tr>'
            '<tr>'
            '<td style="padding:10px;background:#f9f9f9;border:1px solid #e0e0e0;'
            'font-weight:bold;">&#128273; Parol</td>'
            '<td style="padding:10px;border:1px solid #e0e0e0;font-size:18px;'
            'letter-spacing:2px;font-weight:bold;color:#875A7B;">' + password + '</td>'
            '</tr>'
            '</table>'

            '<div style="background:#fff8e1;border-left:4px solid #ffc107;'
            'padding:12px 16px;margin:20px 0;border-radius:4px;">'
            '<strong>&#9888;&#65039; Vacib:</strong> Daxil olduqdan sonra '
            'profili&#241;izi doldurun v&#601; <strong>Complete</strong> '
            'd&#252;ym&#601;sin&#601; bas&#305;n.'
            '</div>'

            '<div style="text-align:center;margin-top:30px;">'
            '<a href="' + login_url + '" style="background-color:#875A7B;color:#ffffff;'
            'padding:14px 32px;text-decoration:none;border-radius:6px;'
            'font-size:16px;font-weight:bold;display:inline-block;">'
            'Odoo-ya Daxil Ol'
            '</a>'
            '</div>'
            '</div>'

            '<div style="background:#f5f5f5;padding:16px;text-align:center;'
            'font-size:12px;color:#999;">'
            'Bu m&#601;ktub avtomatik g&#246;nd&#601;rilib. '
            'Z&#601;hm&#601;t olmasa cavab vermy&#601;in.'
            '</div>'
            '</div>'
        )

        self.env['mail.mail'].sudo().create({
            'subject': _('Welcome to Odoo – Your Login Details'),
            'body_html': body,
            'email_to': user_email,
            'email_from': from_email,
        }).send()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Invite Sent'),
                'message': _('Login credentials have been sent to %s') % self.email,
                'type': 'success',
                'sticky': False,
            },
        }