# -*- coding: utf-8 -*-
from odoo import models

#: Səsli qeydin standart maksimum müddəti (saniyə). Odoo-nun öz limiti 60 saniyədir.
DEFAULT_MAX_DURATION = 300


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        """Maksimum yazma müddətini web client-ə (session) ötürür.

        Frontend-də `session.voice_note_max_duration` kimi oxunur
        (bax: static/src/voice_recorder_patch.js).
        """
        result = super().session_info()
        result['voice_note_max_duration'] = self._get_voice_note_max_duration()
        return result

    def _get_voice_note_max_duration(self):
        param = self.env['ir.config_parameter'].sudo().get_param(
            'chatter_voice_note.max_duration', DEFAULT_MAX_DURATION)
        try:
            duration = int(param)
        except (TypeError, ValueError):
            return DEFAULT_MAX_DURATION
        return duration if duration > 0 else DEFAULT_MAX_DURATION
