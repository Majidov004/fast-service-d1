from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class AccessConfigLine(models.Model):
    """
    Bir istifadəçi üçün bir model haqqında icazə sətri.

    Yanaşma (Yol 2 — Qlobal qadağa):
    --------------------------------
    User-in başqa qruplardan (məs. 'Internal User') gələn icazələrini
    yan keçmək üçün biz QLOBAL ir.rule istifadə edirik.

    ir.rule-da `groups` boş olduqda → o rule HƏR userə tətbiq olunur,
    qrupundan asılı olmayaraq. Bizim halda biz domain-ə user-in id-sini
    əlavə edirik və "yalnız bu userin sənədləri filter olunsun" məntiqi
    qururuq:

      domain = [
          '|',
              ('create_uid', '!=', <bu_user_id>),  # bu user deyilsə → toxunma
              <real_filter>                        # bu userdirsə → filter tətbiq et
      ]

    Bu sayədə:
      * Digər userlər heç bir təsir görmür
      * Bu user isə qlobal rule ilə məhdudlaşdırılır, qruplardan asılı deyil
    """
    _name = 'access.config.line'
    _description = 'İcazə Sətri'

    config_id = fields.Many2one(
        'access.config',
        string='Konfiqurasiya',
        required=True,
        ondelete='cascade',
        index=True,
    )

    user_id = fields.Many2one(
        related='config_id.user_id',
        store=True,
        readonly=True,
        index=True,
    )

    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
        ondelete='cascade',
        help="Hansı modeldə (sənəd növündə) icazə təyin olunsun.\n"
             "Wizard (TransientModel) modelləri də seçilə bilər — onlar üçün "
             "yalnız ACL (oxu/yaz/yarat) yaranır, record filtri tətbiq olunmur."
    )

    model_name = fields.Char(
        related='model_id.model',
        store=True,
        readonly=True,
    )

    # ------------------------------------------------------------
    # CRUD icazələri
    # ------------------------------------------------------------
    perm_read = fields.Boolean(
        string='Oxumaq',
        default=True,
        help="User bu modeli görə bilər və oxuya bilər"
    )
    perm_write = fields.Boolean(
        string='Redaktə',
        default=False,
        help="User bu modelin sənədlərini redaktə edə bilər"
    )
    perm_create = fields.Boolean(
        string='Yaratmaq',
        default=False,
        help="User bu modeldə yeni sənəd yarada bilər"
    )
    perm_unlink = fields.Boolean(
        string='Silmək',
        default=False,
        help="User bu modeldə sənəd silə bilər"
    )

    # ------------------------------------------------------------
    # Record filter (öz sənədləri / əlavə userlər)
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
        help="Hansı sənədləri görəcəyini təyin edir"
    )

    user_field_id = fields.Many2one(
        'ir.model.fields',
        string='Məsul sahə',
        domain="[('model_id', '=', model_id), "
               "('ttype', 'in', ['many2one', 'many2many'])]",
        help="Bu sənədi kimin görəcəyini təyin edən sahə.\n"
             "Sahə bağlana bilər: res.users, res.partner, hr.employee və s.\n"
             "Boş qoyulsa 'create_uid' (yaradan) istifadə olunur."
    )

    visible_user_ids = fields.Many2many(
        'res.users',
        'access_line_visible_users_rel',
        'line_id',
        'user_id',
        string='Əlavə görünən userlər',
        help="Bu user öz sənədlərindən başqa burada seçilən userlərin "
             "sənədlərini də görəcək"
    )

    active = fields.Boolean(
        string='Aktiv',
        default=True,
        help="Deaktiv olduqda bu sətrin yaratdığı qaydalar işləmir"
    )

    # ------------------------------------------------------------
    # Status filter (hansı statuslarda olan sənədlər görünsün?)
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
        'access.status.value',
        'line_id',
        string='İcazə verilən status dəyərləri',
    )
    available_values_hint = fields.Char(
        compute='_compute_available_values_hint',
        string='Mövcud dəyərlər',
        help="Seçilən sahənin mövcud dəyərləri (məlumat üçün)",
    )

    # ------------------------------------------------------------
    # Texniki sahələr (avtomatik yaranan ACL/rule referansları)
    # ------------------------------------------------------------
    access_id = fields.Many2one(
        'ir.model.access',
        string='Yaradılmış ACL',
        readonly=True,
        ondelete='set null',
    )
    rule_id = fields.Many2one(
        'ir.rule',
        string='Yaradılmış Record Rule',
        readonly=True,
        ondelete='set null',
    )

    _sql_constraints = [
        (
            'unique_config_model',
            'UNIQUE(config_id, model_id)',
            'Bu model artıq əlavə edilib! Eyni model üçün iki sətir ola bilməz.'
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
        """Status sahəsi dəyişdikdə seçilmiş dəyərləri sıfırla."""
        self.status_value_ids = [(5, 0, 0)]

    @api.depends('status_field_id', 'model_name')
    def _compute_available_values_hint(self):
        """Seçilən status sahəsinin mövcud dəyərlərini göstər (məlumat üçün)."""
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

    @api.onchange('filter_mode')
    def _onchange_filter_mode(self):
        """Filter 'all' olduqda user_field və əlavə userləri sıfırla."""
        if self.filter_mode == 'all':
            self.visible_user_ids = [(5, 0, 0)]
        if self.filter_mode != 'own_plus':
            self.visible_user_ids = [(5, 0, 0)]

    @api.constrains('filter_mode', 'user_field_id', 'model_id')
    def _check_filter_field(self):
        for rec in self:
            if rec.filter_mode in ('own', 'own_plus'):
                # user_field_id boşdursa create_uid-ə düşəcək
                # amma ən azı modelin create_uid sahəsi olduğunu yoxlayaq
                # (bütün modellərdə var, amma yenə də)
                if rec.user_field_id and rec.user_field_id.model_id != rec.model_id:
                    raise ValidationError(_(
                        "Seçilən 'Məsul sahə' bu modelə aid deyil!"
                    ))

    @api.constrains('visible_user_ids', 'filter_mode')
    def _check_visible_users(self):
        for rec in self:
            if rec.visible_user_ids and rec.filter_mode != 'own_plus':
                raise ValidationError(_(
                    "Əlavə userlər yalnız 'Öz sənədləri + seçilən userlərin "
                    "sənədləri' rejimində seçilə bilər."
                ))

    @api.constrains('user_id', 'visible_user_ids')
    def _check_self_in_visible(self):
        for rec in self:
            if rec.user_id and rec.user_id in rec.visible_user_ids:
                raise ValidationError(_(
                    "İstifadəçinin özünü 'Əlavə görünən userlər' siyahısına "
                    "əlavə etməyə ehtiyac yoxdur — onsuz da öz sənədlərini görür."
                ))

    # ------------------------------------------------------------
    # Köməkçi: user-i təyin edən sahənin adını qaytar
    # ------------------------------------------------------------
    def _get_user_field_path(self):
        """
        Domain-də user-i göstərən path-i qaytarır.
        Müxtəlif relation tiplərini idarə edir:
          * res.users        → field_name (birbaşa)
          * res.partner      → field_name.user_ids
          * hr.employee      → field_name.user_id
          * Digər modellər   → field_name.user_id (cəhd edirik)
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
            # Custom modellər üçün user_id sahəsi olduğunu fərz edirik
            return f"{field_name}.user_id"

    # ------------------------------------------------------------
    # Domain qurulması (qlobal rule üçün)
    # ------------------------------------------------------------
    def _build_domain(self):
        """
        Qlobal rule üçün domain qurur.

        İki müstəqil şərt AND ilə birləşir:
          1. User ownership filteri (filter_mode: own / own_plus)
          2. Status filteri (status_field_id + status_value_ids)

        Rule qlobaldır — domain_force Python ternary ilə yalnız hədəf
        user üçün aktiv edilir; başqa userlər [(1,'=',1)] alır.
        """
        self.ensure_one()
        target_uid = self.user_id.id

        conditions = []

        # 1. User ownership filter
        if self.filter_mode != 'all':
            field_path = self._get_user_field_path()
            allowed_ids = [target_uid]
            if self.filter_mode == 'own_plus':
                allowed_ids.extend(self.visible_user_ids.ids)
            ids_str = ", ".join(str(i) for i in allowed_ids)
            conditions.append(f"('{field_path}', 'in', [{ids_str}])")

        # 2. Status filter
        if self.status_field_id and self.status_value_ids:
            vals = [v.value for v in self.status_value_ids]
            vals_str = ", ".join(f"'{v}'" for v in vals)
            conditions.append(f"('{self.status_field_id.name}', 'in', [{vals_str}])")

        if not conditions:
            return "[(1, '=', 1)]"

        inner_filter = "[" + ", ".join(conditions) + "]"
        return f"{inner_filter} if user.id == {target_uid} else [(1, '=', 1)]"

    # ------------------------------------------------------------
    # Tətbiq və təmizləmə
    # ------------------------------------------------------------
    def _apply(self):
        """
        Bu line üçün ACL və qlobal rule yarat/yenilə.
        """
        self.ensure_one()

        # ----------- ACL hissəsi -----------
        # ACL üçün biz user-in OWN qrupunu istifadə etməliyik.
        # Çünki ACL qlobal ola bilməz — bir qrupa bağlanmalıdır.
        # Amma user-in başqa qruplarından icazə gəlirsə ACL bunu yan keçmir.
        # Buna görə ACL yalnız "icazə vermək" üçün işləyir; "qadağan etmək"
        # üçün yox. Qadağa rule ilə həyata keçir.
        #
        # Strategiya:
        #   * Hər user üçün gizli bir qrup yaradırıq (bir dəfəlik)
        #   * ACL bu qrupa bağlanır
        #   * ACL yalnız MÜSBƏT icazə verir (perm_read=True və s.)
        #   * Qadağa qlobal rule ilə işləyir
        group = self._get_or_create_user_group()

        acl_vals = {
            'name': f'access_acl_u{self.user_id.id}_m{self.model_id.id}',
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
        # filter_mode != 'all' VƏ YA status filteri varsa rule yarat
        has_status_filter = bool(self.status_field_id and self.status_value_ids)
        needs_rule = (self.filter_mode != 'all' or has_status_filter) and self.active
        if not needs_rule:
            # Rule lazım deyil, varsa sil
            if self.rule_id and self.rule_id.exists():
                self.rule_id.sudo().unlink()
            rule = self.env['ir.rule']
        else:
            rule_vals = {
                'name': f'access_rule_u{self.user_id.id}_m{self.model_id.id}',
                'model_id': self.model_id.id,
                'domain_force': self._build_domain(),
                'groups': [(5, 0, 0)],  # QLOBAL — heç bir qrupa bağlı deyil
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

        # Referansları saxla
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
        self.sudo().write({
            'access_id': False,
            'rule_id': False,
        })

    def _get_or_create_user_group(self):
        """
        Bu user üçün gizli bir qrup yaradır (yalnız bizim ACL-lər üçün).
        Qrup adı: '[AccessMgr] <username> (id:N)'

        Odoo 18-də res.groups.name jsonb olduğu üçün axtarış SQL ilə edilir.
        """
        self.ensure_one()
        Group = self.env['res.groups'].sudo()
        uid = self.user_id.id

        # SQL ilə mövcud qrupu axtar (jsonb-aware)
        self.env.cr.execute("""
            SELECT rg.id
            FROM res_groups rg
            JOIN res_groups_users_rel rgu ON rgu.gid = rg.id
            WHERE rgu.uid = %s
              AND rg.name->>'en_US' LIKE '[AccessMgr]%%'
            LIMIT 1
        """, (uid,))
        row = self.env.cr.fetchone()
        if row:
            return Group.browse(row[0])

        # Yenisi yarat
        group = Group.create({
            'name': f'[AccessMgr] {self.user_id.name} (id:{uid})',
            'users': [(4, uid)],
        })
        return group

    def unlink(self):
        """Line silinəndə ACL və rule-u da sil."""
        for rec in self:
            rec._cleanup()
        result = super().unlink()
        self.env.registry.clear_cache()
        return result
