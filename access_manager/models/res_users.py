from odoo import models, fields, api


class ResUsers(models.Model):
    """
    İstifadəçiyə icazə vəzifələri (rolları) əlavə edir.

    `access_role_ids` access.role.member_user_ids ilə EYNİ relation cədvəlini
    bölüşür — yəni vəzifəni istər istifadəçi formasından, istər vəzifə
    formasından təyin etmək olar.

    İstifadəçinin vəzifələri dəyişdikdə tətbiq olunmuş vəzifələrin qrup
    üzvlüyü yenidən sinxronlaşdırılır və keş təmizlənir ki, icazələr dərhal
    təsir göstərsin.
    """
    _inherit = 'res.users'

    access_role_ids = fields.Many2many(
        'access.role',
        'access_role_users_rel',
        'user_id',
        'role_id',
        string='İcazə Vəzifələri',
        help="Bu istifadəçinin icazə vəzifələri (rolları). "
             "Vəzifə təyin etdikdə həmin vəzifənin bütün icazələrini avtomatik alır.",
    )

    def _resync_access_roles(self):
        """Tətbiq olunmuş bütün vəzifələrin qrup üzvlüyünü yenidən qur."""
        roles = self.env['access.role'].sudo().search([('state', '=', 'applied')])
        for role in roles:
            role._sync_group_members()
        self.env.registry.clear_cache()

    def write(self, vals):
        res = super().write(vals)
        if 'access_role_ids' in vals:
            self._resync_access_roles()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        if any('access_role_ids' in (vals or {}) for vals in vals_list):
            users._resync_access_roles()
        return users
