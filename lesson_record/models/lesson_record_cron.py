from datetime import datetime
import logging
import pytz

from markupsafe import Markup
from odoo import models, api

_logger = logging.getLogger(__name__)


class LessonRecordCron(models.Model):
    _inherit = 'lesson.record'

    @api.model
    def _cron_notify_incomplete_lessons(self):
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')
        now_local = datetime.now(user_tz)
        current_time_float = now_local.hour + now_local.minute / 60.0
        today = now_local.date()

        lessons = self.search([
            ('lesson_date', '=', today),
            ('end_time', '<', current_time_float),
            ('state', '=', 'scheduled'),
        ])

        _logger.info("CRON: tapılan dərslər = %s", lessons.ids)

        for lesson in lessons:
            lesson._send_incomplete_notification()

    def _send_incomplete_notification(self):
        self.ensure_one()

        if not self.teacher_id:
            return

        teacher = self.teacher_id
        partner = teacher.user_id.partner_id if teacher.user_id else teacher.address_id

        if not partner:
            _logger.warning("NOTIFICATION SKIP: partner yoxdur — dərs id=%s", self.id)
            return

        admin_partner = self.env.ref('base.user_admin').partner_id

        mention = Markup(
            f'<a href="/web#model=res.partner&amp;id={partner.id}" '
            f'data-oe-model="res.partner" data-oe-id="{partner.id}" '
            f'class="o_mail_redirect">@{partner.name}</a>'
        )

        body = Markup(
            f'⚠️ {mention} <b>{self.name}</b> dərsi '
            f'{self.lesson_time_display} vaxtında bitməli idi, '
            f'lakin hələ tamamlanmayıb. Zəhmət olmasa statusu yeniləyin.'
        )

        # 1. Administrators kanalına göndər → Push Notification işləyir
        channel = self.env.ref('mail.channel_admin').sudo()
        channel.message_post(
            body=body,
            author_id=admin_partner.id,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
            partner_ids=partner.ids,
        )

        # 2. Dərsin chatter-inə də göndər → Sənəd üzərində görünsün
        self.sudo().message_post(
            body=body,
            author_id=admin_partner.id,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )

        _logger.info("NOTIFICATION: göndərildi — dərs=%s, müəllim=%s", self.name, partner.name)