from odoo import models, fields, api, _
from odoo.exceptions import UserError
from lxml import etree
import logging

_logger = logging.getLogger(__name__)


class AccessRole(models.Model):
    """
    Vəzifə / Rol əsaslı icazə konfiqurasiyası.

    Bir vəzifə (məs. 'Müəllim') üçün icazələri BİR DƏFƏ təyin edirik,
    sonra istifadəçilərə həmin vəzifəni veririk — hamısı eyni icazəni alır.

    Texniki yanaşma:
      * Hər vəzifə üçün real bir res.groups yaradılır → '[AccessRole] <ad>'.
      * ACL bu qrupa bağlanır → üzvlərə CRUD verir (TOPLAMA / union məntiqi).
      * Record filteri QLOBAL ir.rule ilə işləyir; domain ternary:
            <filter> if <qrup_id> in user.groups_id.ids else [(1,'=',1)]
        yəni yalnız bu qrupun üzvləri filtrlənir, başqaları toxunulmur.
      * 'own' rejimində user.id DİNAMİK işlənir → hər üzv yalnız ÖZ sənədini görür.
      * Fərdi istisna üçün mövcud access.config (per-user) bu vəzifənin ÜSTÜNDƏN işləyir:
          - əlavə icazə (ACL union) → işləyir
          - əlavə record filtri (qlobal rule AND) → işləyir
          - qrupun verdiyi CRUD-u geri almaq mümkün deyil → istifadəçini vəzifədən çıxarın.

    Qeyd: '[AccessRole]' prefiksi access.config.line-dakı '[AccessMgr]%' SQL
    axtarışı ilə TOQQUŞMUR (per-user qrup məntiqi pozulmur).
    """
    _name = 'access.role'
    _description = 'İcazə Vəzifəsi (Rol)'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Vəzifə adı', required=True, tracking=True)

    group_id = fields.Many2one(
        'res.groups',
        string='Texniki qrup',
        readonly=True,
        ondelete='set null',
        help="Bu vəzifənin arxasındakı real Odoo qrupu (avtomatik idarə olunur).",
    )

    member_user_ids = fields.Many2many(
        'res.users',
        'access_role_users_rel',
        'role_id',
        'user_id',
        string='Üzvlər',
        help="Bu vəzifəyə malik istifadəçilər. Əlavə/çıxarış (tətbiqdən sonra) "
             "dərhal təsir edir.",
    )

    line_ids = fields.One2many(
        'access.role.line',
        'role_id',
        string='İcazə Sətirləri',
        domain=[('is_dependency', '=', False)],
    )

    dependency_line_ids = fields.One2many(
        'access.role.line',
        'role_id',
        string='Alt Asılılıqlar',
        domain=[('is_dependency', '=', True)],
        help="'Asılılıqları Tap' düyməsi ilə avtomatik tapılan modellər.",
    )

    member_count = fields.Integer(compute='_compute_counts', string='Üzv sayı')
    line_count = fields.Integer(compute='_compute_counts', string='Sətir sayı')

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

    last_apply_date = fields.Datetime(string='Son tətbiq tarixi', readonly=True)
    note = fields.Text(string='Qeyd')

    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)', 'Bu adla vəzifə artıq mövcuddur!'),
    ]

    @api.depends('member_user_ids', 'line_ids', 'dependency_line_ids')
    def _compute_counts(self):
        for rec in self:
            rec.member_count = len(rec.member_user_ids)
            rec.line_count = len(rec.line_ids) + len(rec.dependency_line_ids)

    def _all_lines(self):
        """Əsas + alt asılılıq sətirlərinin hamısı (backend tətbiq üçün)."""
        self.ensure_one()
        return self.line_ids | self.dependency_line_ids

    # ------------------------------------------------------------
    # Qrup həyat dövrü
    # ------------------------------------------------------------
    def _ensure_group(self):
        """Vəzifənin real qrupunu qaytarır, yoxdursa yaradır."""
        self.ensure_one()
        if self.group_id and self.group_id.exists():
            return self.group_id
        group = self.env['res.groups'].sudo().create({
            'name': f'[AccessRole] {self.name}',
        })
        self.sudo().write({'group_id': group.id})
        return group

    def _sync_group_members(self):
        """
        Qrup üzvlüyünü member_user_ids ilə eyniləşdirir.
        Admin (uid=1) heç vaxt vəzifə qrupuna salınmır.
        """
        self.ensure_one()
        if not (self.group_id and self.group_id.exists()):
            return
        uids = [u.id for u in self.member_user_ids if u.id != 1]
        self.group_id.sudo().write({'users': [(6, 0, uids)]})

    # ------------------------------------------------------------
    # Əsas əməliyyatlar
    # ------------------------------------------------------------
    def action_apply(self):
        """
        Vəzifəni DB-yə tətbiq edir:
          * Qrupu yaradır və üzvləri sinxronlaşdırır
          * Hər line üçün ACL (qrupa bağlı) + qlobal record rule yaradır/yeniləyir
        """
        for rec in self:
            if not rec.name:
                raise UserError(_("Vəzifə adı tələb olunur!"))
            rec._ensure_group()
            rec._sync_group_members()
            for line in rec._all_lines():
                line._apply()
            rec.write({
                'state': 'applied',
                'last_apply_date': fields.Datetime.now(),
            })

        # Cache təmizlə ki, dəyişikliklər dərhal görünsün
        self.env.registry.clear_cache()
        return self._notify(
            _('Uğurlu!'), _('Vəzifə icazələri tətbiq edildi.'), 'success')

    def action_reset(self):
        """Bütün line-ların ACL/rule-larını silir və qrupu boşaldır."""
        for rec in self:
            for line in rec._all_lines():
                line._cleanup()
            if rec.group_id and rec.group_id.exists():
                rec.group_id.sudo().write({'users': [(5, 0, 0)]})
            rec.write({'state': 'draft', 'last_apply_date': False})

        self.env.registry.clear_cache()
        return self._notify(
            _('Sıfırlandı'), _('Vəzifə icazələri silindi.'), 'warning')

    # ------------------------------------------------------------
    # Asılılıqların avtomatik aşkarlanması
    # ------------------------------------------------------------
    def _discover_model_deps(self, model_name):
        """
        Verilən model üçün 'alt asılılıqları' tapır:
          * related — form/list view-da istinad olunan əlaqəli (qeyri-transient) modellər
          * wizards — bu modelə aid wizard (transient) modellər

        Tam deyil: object-metodla (type="object" düymə) açılan bəzi wizard-ları
        statik tapmaq olmur. Ona görə 4 üsul birləşdirilir (aşağıda).
        Hər biri try/except ilə qorunur ki, biri uğursuz olsa, qalanları işləsin.
        """
        related, wizards = set(), set()
        if model_name not in self.env:
            return related, wizards
        Model = self.env[model_name].sudo()

        def _classify(m):
            if m and m in self.env and m != model_name:
                if self.env[m]._transient:
                    wizards.add(m)
                else:
                    related.add(m)

        # 1) Form/list view-da istinad olunan modellər
        try:
            res = Model.get_views([(False, 'form'), (False, 'list')])
            for m in res.get('models', {}):
                _classify(m)
        except Exception as e:
            _logger.warning("Asılılıq aşkarı (get_views) uğursuz [%s]: %s", model_name, e)

        # 2) Form-dakı action düymələrinin açdığı act_window modelləri
        try:
            view = Model.get_view(view_type='form')
            arch = view['arch']
            node = etree.fromstring(arch.encode() if isinstance(arch, str) else arch)
            for btn in node.xpath('//button[@type="action"]'):
                name = btn.get('name')
                if name and name.isdigit():
                    act = self.env['ir.actions.act_window'].sudo().browse(int(name))
                    if act.exists() and act.res_model:
                        _classify(act.res_model)
        except Exception as e:
            _logger.warning("Asılılıq aşkarı (buttons) uğursuz [%s]: %s", model_name, e)

        # 3) Bu modelə bağlı act_window action-ları (binding və ya res_model)
        try:
            actions = self.env['ir.actions.act_window'].sudo().search([
                '|', ('binding_model_id.model', '=', model_name),
                     ('res_model', '=', model_name),
            ])
            for act in actions:
                if act.res_model:
                    _classify(act.res_model)
        except Exception as e:
            _logger.warning("Asılılıq aşkarı (actions) uğursuz [%s]: %s", model_name, e)

        # 4) Adlandırma evristikası: '<model>.*' transient modellər (wizard-lar)
        try:
            imodels = self.env['ir.model'].sudo().search([
                ('model', '=like', model_name + '.%'),
                ('transient', '=', True),
            ])
            for im in imodels:
                wizards.add(im.model)
        except Exception as e:
            _logger.warning("Asılılıq aşkarı (naming) uğursuz [%s]: %s", model_name, e)

        return related, wizards

    def _internal_user_has_read(self, model_name):
        """
        Daxili istifadəçi (base.group_user və onun genişləndirdiyi qruplar) bu
        modeli onsuz da oxuya bilirmi? Belədirsə, vəzifəyə əlavə etməyə ehtiyac
        yoxdur (res.*, ir.*, mail.*, contact.* və s. — onsuz da əlçatandır).
        """
        group_user = self.env.ref('base.group_user', raise_if_not_found=False)
        if not group_user:
            return False
        group_ids = (group_user | group_user.trans_implied_ids).ids
        return bool(self.env['ir.model.access'].sudo().search_count([
            ('model_id.model', '=', model_name),
            ('perm_read', '=', True),
            ('group_id', 'in', group_ids),
        ]))

    def action_discover_dependencies(self):
        """
        Sətirlərdəki modellərin alt asılılıqlarını TRANSITIV (dərinə) tapıb
        'Alt Asılılıqlar' tabına əlavə edir — bir klikdə bütün zəncir:
          model → form/wizard asılılığı → onun da asılılığı → ...
          * Əlaqəli modellər → yalnız Oxu
          * Wizard modellər   → Oxu + Yaz + Yarat
        Daxili istifadəçinin onsuz da malik olduğu modellər (base.group_user)
        ötürülür ki, tab şişməsin. Yalnız bir dəfə basmaq kifayətdir.
        """
        self.ensure_one()
        IrModel = self.env['ir.model'].sudo()

        seen = set(self._all_lines().mapped('model_name'))  # artıq roldadır
        to_create = {}      # model_name -> is_wizard (əlavə olunacaq yenilər)
        frontier = list(seen)  # əvvəlcə mövcud modelləri tara
        MAX_ITER = 15
        MAX_NEW = 300

        for _i in range(MAX_ITER):
            new_frontier = []
            for model_name in frontier:
                if not model_name:
                    continue
                related, wizards = self._discover_model_deps(model_name)
                for m, is_wizard in [(x, False) for x in related] + [(x, True) for x in wizards]:
                    if m in seen:
                        continue
                    seen.add(m)
                    # Müəllim onsuz da oxuya bilirsə → əlavə etmə, dərinə də getmə
                    if self._internal_user_has_read(m):
                        continue
                    to_create[m] = to_create.get(m, False) or is_wizard
                    new_frontier.append(m)  # məhdud modeli dərinə tara
                if len(to_create) >= MAX_NEW:
                    break
            if not new_frontier or len(to_create) >= MAX_NEW:
                break
            frontier = new_frontier

        created = 0
        for model_name, is_wizard in to_create.items():
            imodel = IrModel.search([('model', '=', model_name)], limit=1)
            if not imodel:
                continue
            self.env['access.role.line'].create({
                'role_id': self.id,
                'model_id': imodel.id,
                'perm_read': True,
                'perm_write': is_wizard,
                'perm_create': is_wizard,
                'perm_unlink': False,
                'filter_mode': 'all',
                'is_dependency': True,  # → 'Alt Asılılıqlar' tabına düşür
            })
            created += 1

        if created:
            msg = _("%s alt asılılıq tapıldı və 'Alt Asılılıqlar' tabına əlavə edildi. "
                    "Yoxlayıb 'İcazələri Tətbiq Et' basın.") % created
            ntype = 'success'
        else:
            msg = _("Yeni asılılıq tapılmadı (hamısı artıq əlavə edilib və ya əlçatandır).")
            ntype = 'info'
        return self._notify(_('Asılılıqlar'), msg, ntype)

    def write(self, vals):
        res = super().write(vals)
        # Ad dəyişdisə qrup adını da yenilə
        if 'name' in vals:
            for rec in self:
                if rec.group_id and rec.group_id.exists():
                    rec.group_id.sudo().write({'name': f'[AccessRole] {rec.name}'})
        # Üzvlük dəyişdisə qrupu sinxronlaşdır və keşi təmizlə (dərhal təsir)
        if 'member_user_ids' in vals:
            for rec in self:
                if rec.state == 'applied':
                    rec._sync_group_members()
            self.env.registry.clear_cache()
        return res

    def unlink(self):
        """Vəzifə silinəndə ACL/rule-ları və texniki qrupu da sil."""
        groups = self.env['res.groups']
        for rec in self:
            for line in rec._all_lines():
                line._cleanup()
            if rec.group_id and rec.group_id.exists():
                groups |= rec.group_id

        result = super().unlink()
        if groups:
            groups.sudo().unlink()
        self.env.registry.clear_cache()
        return result

    # ------------------------------------------------------------
    # Köməkçi
    # ------------------------------------------------------------
    def _notify(self, title, message, ntype):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': ntype,
                'sticky': False,
            },
        }
