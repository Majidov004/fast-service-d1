from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class AccessRoleLine(models.Model):
    """
    Bir vəzifə üçün bir model haqqında icazə sətri.

    access.config.line ilə eyni quruluşdadır, lakin:
      * Bir userə yox, vəzifənin BÜTÜN üzvlərinə tətbiq olunur.
      * ACL vəzifənin real qrupuna (role_id.group_id) bağlanır.
      * Qlobal rule-un domain-i "qrup üzvüdürsə filter" şəklindədir:
            <filter> if <qrup_id> in user.groups_id.ids else [(1,'=',1)]
      * 'own' rejimində DİNAMİK user.id istifadə olunur ki, hər üzv yalnız
        ÖZ sənədlərini görsün (statik üzv siyahısı təhlükəlidir — hər kəs
        bir-birinin sənədini görərdi).
    """
    _name = 'access.role.line'
    _description = 'Vəzifə İcazə Sətri'

    role_id = fields.Many2one(
        'access.role',
        string='Vəzifə',
        required=True,
        ondelete='cascade',
        index=True,
    )

    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
        ondelete='cascade',
        help="Hansı modeldə (sənəd növündə) icazə təyin olunsun.\n"
             "Wizard (TransientModel) modelləri də seçilə bilər — onlar üçün "
             "yalnız ACL (oxu/yaz/yarat) yaranır, record filtri tətbiq olunmur.",
    )
    model_name = fields.Char(related='model_id.model', store=True, readonly=True)

    # ------------------------------------------------------------
    # CRUD icazələri
    # ------------------------------------------------------------
    perm_read = fields.Boolean(
        string='Oxumaq', default=True,
        help="Üzvlər bu modeli görə və oxuya bilər")
    perm_write = fields.Boolean(
        string='Redaktə', default=False,
        help="Üzvlər bu modelin sənədlərini redaktə edə bilər")
    perm_create = fields.Boolean(
        string='Yaratmaq', default=False,
        help="Üzvlər bu modeldə yeni sənəd yarada bilər")
    perm_unlink = fields.Boolean(
        string='Silmək', default=False,
        help="Üzvlər bu modeldə sənəd silə bilər")

    # ------------------------------------------------------------
    # Record filter
    # ------------------------------------------------------------
    filter_mode = fields.Selection(
        [
            ('all', 'Hamısını görsün'),
            ('own', 'Yalnız öz sənədlərini görsün'),
            ('own_plus', 'Öz sənədləri + seçilən userlərin sənədləri'),
        ],
        string='Filter rejimi',
        default='all',
        required=True,
        help="Hər üzvün hansı sənədləri görəcəyini təyin edir",
    )

    user_field_id = fields.Many2one(
        'ir.model.fields',
        string='Məsul sahə',
        domain="[('model_id', '=', model_id), "
               "('ttype', 'in', ['many2one', 'many2many'])]",
        help="Bu sənədi kimin görəcəyini təyin edən sahə.\n"
             "Sahə bağlana bilər: res.users, res.partner, hr.employee və s.\n"
             "Boş qoyulsa 'create_uid' (yaradan) istifadə olunur.",
    )

    visible_user_ids = fields.Many2many(
        'res.users',
        'access_role_line_visible_users_rel',
        'line_id',
        'user_id',
        string='Əlavə görünən userlər',
        help="Üzvlər öz sənədlərindən başqa burada seçilən userlərin "
             "sənədlərini də görəcək",
    )

    active = fields.Boolean(
        string='Aktiv', default=True,
        help="Deaktiv olduqda bu sətrin yaratdığı qaydalar işləmir")

    is_dependency = fields.Boolean(
        string='Alt asılılıq',
        default=False,
        help="True olduqda bu sətir 'Asılılıqları Tap' düyməsi ilə avtomatik "
             "tapılıb və 'Alt Asılılıqlar' tabında göstərilir.")

    # ------------------------------------------------------------
    # Status filter
    # ------------------------------------------------------------
    status_field_id = fields.Many2one(
        'ir.model.fields',
        string='Status sahəsi',
        domain="[('model_id', '=', model_id), ('ttype', '=', 'selection')]",
        ondelete='set null',
        help="Modelin selection tipli sahəsini seçin — yalnız bu statuslardakı "
             "sənədlər görünəcək. Boş qoyulsa status filtri işləmir.",
    )
    status_value_ids = fields.One2many(
        'access.role.status.value',
        'line_id',
        string='İcazə verilən status dəyərləri',
    )
    available_values_hint = fields.Char(
        compute='_compute_available_values_hint',
        string='Mövcud dəyərlər',
        help="Seçilən sahənin mövcud dəyərləri (məlumat üçün)",
    )

    # ------------------------------------------------------------
    # Texniki sahələr
    # ------------------------------------------------------------
    access_id = fields.Many2one(
        'ir.model.access', string='Yaradılmış ACL',
        readonly=True, ondelete='set null')
    rule_id = fields.Many2one(
        'ir.rule', string='Yaradılmış Record Rule',
        readonly=True, ondelete='set null')

    _sql_constraints = [
        (
            'unique_role_model',
            'UNIQUE(role_id, model_id)',
            'Bu model bu vəzifə üçün artıq əlavə edilib! Eyni model üçün iki sətir ola bilməz.'
        ),
    ]

    # ------------------------------------------------------------
    # Onchange və validasiyalar
    # ------------------------------------------------------------
    @api.onchange('model_id')
    def _onchange_model_id(self):
        """Model dəyişdikdə user_field, status field və əlavə userləri sıfırla."""
        self.user_field_id = False
        self.visible_user_ids = [(5, 0, 0)]
        self.status_field_id = False
        self.status_value_ids = [(5, 0, 0)]
        if self.model_id:
            field = self.env['ir.model.fields'].search([
                ('model_id', '=', self.model_id.id),
                ('name', '=', 'user_id'),
                ('ttype', '=', 'many2one'),
            ], limit=1)
            if field:
                self.user_field_id = field

    @api.onchange('status_field_id')
    def _onchange_status_field_id(self):
        self.status_value_ids = [(5, 0, 0)]

    @api.onchange('filter_mode')
    def _onchange_filter_mode(self):
        if self.filter_mode != 'own_plus':
            self.visible_user_ids = [(5, 0, 0)]

    @api.depends('status_field_id', 'model_name')
    def _compute_available_values_hint(self):
        for rec in self:
            if not rec.status_field_id or not rec.model_name:
                rec.available_values_hint = ''
                continue
            model_name = rec.model_name
            field_name = rec.status_field_id.name
            if model_name not in self.env:
                rec.available_values_hint = ''
                continue
            model_cls = self.env[model_name]
            if field_name not in model_cls._fields:
                rec.available_values_hint = ''
                continue
            selection = model_cls._fields[field_name].selection
            if callable(selection):
                try:
                    selection = selection(model_cls)
                except Exception:
                    selection = []
            parts = [f"'{k}' ({v})" for k, v in (selection or [])]
            rec.available_values_hint = ', '.join(parts)

    @api.constrains('filter_mode', 'user_field_id', 'model_id')
    def _check_filter_field(self):
        for rec in self:
            if rec.filter_mode in ('own', 'own_plus'):
                if rec.user_field_id and rec.user_field_id.model_id != rec.model_id:
                    raise ValidationError(_(
                        "Seçilən 'Məsul sahə' bu modelə aid deyil!"))

    @api.constrains('visible_user_ids', 'filter_mode')
    def _check_visible_users(self):
        for rec in self:
            if rec.visible_user_ids and rec.filter_mode != 'own_plus':
                raise ValidationError(_(
                    "Əlavə userlər yalnız 'Öz sənədləri + seçilən userlərin "
                    "sənədləri' rejimində seçilə bilər."))

    # ------------------------------------------------------------
    # Köməkçi: user-i təyin edən sahənin path-i
    # ------------------------------------------------------------
    def _get_user_field_path(self):
        """
        Domain-də user-i göstərən path-i qaytarır
        (access.config.line ilə eyni məntiq).
        """
        self.ensure_one()
        if not self.user_field_id:
            return 'create_uid'

        field_name = self.user_field_id.name
        relation = self.user_field_id.relation

        if relation == 'res.users':
            return field_name
        elif relation == 'res.partner':
            return f"{field_name}.user_ids"
        elif relation == 'hr.employee':
            return f"{field_name}.user_id"
        else:
            return f"{field_name}.user_id"

    # ------------------------------------------------------------
    # Domain qurulması (qlobal rule üçün)
    # ------------------------------------------------------------
    def _build_domain(self):
        """
        Qlobal rule domain-i:
            <filter> if <qrup_id> in user.groups_id.ids else [(1,'=',1)]

        DİQQƏT: 'own' rejimində 'user.id' DİNAMİK olaraq domain mətninə
        yazılır (dəyər kimi yox, ifadə kimi) → hər üzv yalnız ÖZ sənədini
        görür. Statik üzv siyahısı işlətsək, hər müəllim bir-birinin
        sənədini görərdi (təhlükəsizlik xətası).
        """
        self.ensure_one()
        gid = self.role_id.group_id.id

        conditions = []

        # 1. Ownership filter (DİNAMİK user.id)
        if self.filter_mode != 'all':
            field_path = self._get_user_field_path()
            allowed = ["user.id"]  # cari user (eval zamanı)
            if self.filter_mode == 'own_plus':
                allowed += [str(i) for i in self.visible_user_ids.ids]
            ids_str = ", ".join(allowed)
            conditions.append(f"('{field_path}', 'in', [{ids_str}])")

        # 2. Status filter
        if self.status_field_id and self.status_value_ids:
            vals = [v.value for v in self.status_value_ids]
            vals_str = ", ".join(f"'{v}'" for v in vals)
            conditions.append(f"('{self.status_field_id.name}', 'in', [{vals_str}])")

        if not conditions:
            return "[(1, '=', 1)]"

        inner_filter = "[" + ", ".join(conditions) + "]"
        return f"{inner_filter} if {gid} in user.groups_id.ids else [(1, '=', 1)]"

    # ------------------------------------------------------------
    # Tətbiq və təmizləmə
    # ------------------------------------------------------------
    def _apply(self):
        """Bu line üçün ACL (qrupa bağlı) və qlobal rule yarat/yenilə."""
        self.ensure_one()
        group = self.role_id._ensure_group()

        # ----------- ACL hissəsi -----------
        acl_vals = {
            'name': f'access_role_acl_r{self.role_id.id}_m{self.model_id.id}',
            'model_id': self.model_id.id,
            'group_id': group.id,
            'perm_read':   self.perm_read,
            'perm_write':  self.perm_write,
            'perm_create': self.perm_create,
            'perm_unlink': self.perm_unlink,
            'active': self.active,
        }
        if self.access_id and self.access_id.exists():
            self.access_id.sudo().write(acl_vals)
            access = self.access_id
        else:
            access = self.env['ir.model.access'].sudo().create(acl_vals)

        # ----------- Rule hissəsi (QLOBAL) -----------
        has_status_filter = bool(self.status_field_id and self.status_value_ids)
        needs_rule = (self.filter_mode != 'all' or has_status_filter) and self.active
        if not needs_rule:
            if self.rule_id and self.rule_id.exists():
                self.rule_id.sudo().unlink()
            rule = self.env['ir.rule']
        else:
            rule_vals = {
                'name': f'access_role_rule_r{self.role_id.id}_m{self.model_id.id}',
                'model_id': self.model_id.id,
                'domain_force': self._build_domain(),
                'groups': [(5, 0, 0)],  # QLOBAL — qrupa bağlı deyil
                'perm_read':   True,
                'perm_write':  True,
                'perm_create': True,
                'perm_unlink': True,
                'active': self.active,
            }
            if self.rule_id and self.rule_id.exists():
                self.rule_id.sudo().write(rule_vals)
                rule = self.rule_id
            else:
                rule = self.env['ir.rule'].sudo().create(rule_vals)

        self.sudo().write({
            'access_id': access.id,
            'rule_id': rule.id if rule else False,
        })

    def _cleanup(self):
        """ACL və rule-u sil."""
        self.ensure_one()
        if self.rule_id and self.rule_id.exists():
            self.rule_id.sudo().unlink()
        if self.access_id and self.access_id.exists():
            self.access_id.sudo().unlink()
        self.sudo().write({'access_id': False, 'rule_id': False})

    def unlink(self):
        for rec in self:
            rec._cleanup()
        result = super().unlink()
        self.env.registry.clear_cache()
        return result
