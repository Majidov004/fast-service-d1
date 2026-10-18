from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class FieldAccessConfig(models.Model):
    _name = 'field.access.config'
    _description = 'User Sahə Giriş Konfiqurasiyası'
    _rec_name = 'user_id'

    user_id = fields.Many2one(
        'res.users',
        string='İstifadəçi',
        required=True,
        ondelete='cascade',
        help='Bu qaydalar bu istifadəçiyə tətbiq olunacaq'
    )
    active = fields.Boolean(
        string='Aktiv',
        default=True,
        help='Söndürülsə, bu istifadəçi üçün heç bir qayda işləməz'
    )
    line_ids = fields.One2many(
        'field.access.line',
        'config_id',
        string='Sahə Qaydaları'
    )
    note = fields.Text(string='Qeyd')
    line_count = fields.Integer(
        string='Qayda sayı',
        compute='_compute_line_count'
    )

    # _sql_constraints = [
    #     ('unique_user', 'UNIQUE(user_id)',
    #      'Bu istifadəçi üçün artıq konfiqurasiya mövcuddur!'),
    # ]
    @api.constrains('user_id', 'active')
    def _check_unique_active_user(self):
        for rec in self:
            if rec.active:
                existing = self.search([
                    ('user_id', '=', rec.user_id.id),
                    ('active', '=', True),
                    ('id', '!=', rec.id),
                ], limit=1)
                if existing:
                    raise ValidationError(
                        _('Bu istifadəçi üçün artıq aktiv konfiqurasiya mövcuddur!')
                    )

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    def name_get(self):
        return [(r.id, f"Sahə Girişi: {r.user_id.name}") for r in self]

    def toggle_active(self):
        for rec in self:
            rec.active = not rec.active

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env.registry.clear_cache()
        return records

    def write(self, vals):
        res = super().write(vals)
        self.env.registry.clear_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self.env.registry.clear_cache()
        return res

    def toggle_active(self):
        for rec in self:
            rec.active = not rec.active
        self.env.registry.clear_cache()
