from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccessConfig(models.Model):
    """
    Hər istifadəçi üçün bir konfiqurasiya qeydi.
    Bu konfiqurasiya altında həmin user üçün hansı modellərə
    nə qədər icazə verildiyini line-larda saxlayırıq.
    """
    _name = 'access.config'
    _description = 'İstifadəçi İcazə Konfiqurasiyası'
    _rec_name = 'user_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    user_id = fields.Many2one(
        'res.users',
        string='İstifadəçi',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True,
    )

    line_ids = fields.One2many(
        'access.config.line',
        'config_id',
        string='İcazə Sətirləri',
    )

    line_count = fields.Integer(
        string='Sətir sayı',
        compute='_compute_line_count',
    )

    state = fields.Selection(
        [
            ('draft', 'Layihə'),
            ('applied', 'Tətbiq edilib'),
        ],
        string='Status',
        default='draft',
        tracking=True,
        readonly=True,
    )

    last_apply_date = fields.Datetime(
        string='Son tətbiq tarixi',
        readonly=True,
    )

    note = fields.Text(string='Qeyd')

    _sql_constraints = [
        (
            'unique_user',
            'UNIQUE(user_id)',
            'Bu istifadəçi üçün artıq bir konfiqurasiya mövcuddur!'
        ),
    ]

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    # ------------------------------------------------------------
    # Əsas əməliyyatlar
    # ------------------------------------------------------------
    def action_apply(self):
        """
        Bütün line-ları DB-yə tətbiq edir:
          * Hər line üçün qlobal ir.rule yaradır/yeniləyir
          * Hər line üçün ACL yaradır/yeniləyir (user-in öz qrupunda)
        """
        for rec in self:
            if not rec.user_id:
                raise UserError(_("İstifadəçi seçilməlidir!"))

            if rec.user_id.id == 1:
                raise UserError(_(
                    "Admin (uid=1) üçün icazə təyin etmək olmaz! "
                    "Admin bütün məhdudiyyətlərdən kənardadır."
                ))

            for line in rec.line_ids:
                line._apply()

            rec.write({
                'state': 'applied',
                'last_apply_date': fields.Datetime.now(),
            })

        # Cache təmizlə ki, dəyişikliklər dərhal görünsün
        self.env.registry.clear_cache()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Uğurlu!'),
                'message': _('İcazələr tətbiq edildi.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_reset(self):
        """
        Bütün line-ların yaratdığı ACL və rule-ları silir.
        Konfiqurasiya 'draft' statusuna qayıdır.
        """
        for rec in self:
            for line in rec.line_ids:
                line._cleanup()
            rec.write({
                'state': 'draft',
                'last_apply_date': False,
            })

        self.env.registry.clear_cache()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sıfırlandı'),
                'message': _('Bütün icazələr silindi.'),
                'type': 'warning',
                'sticky': False,
            }
        }

    def unlink(self):
        """
        Konfiqurasiya silinməzdən əvvəl bütün ACL və rule-ları təmizlə.
        """
        for rec in self:
            for line in rec.line_ids:
                line._cleanup()

        result = super().unlink()
        self.env.registry.clear_cache()
        return result
