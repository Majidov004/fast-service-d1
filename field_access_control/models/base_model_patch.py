from odoo import models, api, fields
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval
import logging

_logger = logging.getLogger(__name__)

_OP_MAP = {'=': '==', '!=': '!=', '>': '>', '<': '<', '>=': '>=', '<=': '<='}


def _domain_to_py_expr(domain_str):
    """Domain stringini Odoo 18 üçün Python ifadəsinə çevir.

    Odoo 18-də invisible/readonly/required atributları domain kimi yox,
    Python ifadəsi kimi qiymətləndirilir. Boş olmayan list həmişə True
    qaytarır, ona görə [('field','=',val)] → field == val formatına keçmək lazımdır.
    """
    try:
        domain = safe_eval(domain_str or '[]')
        if not domain:
            return None
        parts = []
        for item in domain:
            if item in ('&', '|', '!'):
                continue
            if not isinstance(item, (list, tuple)) or len(item) != 3:
                continue
            field, op, value = item
            if op in ('in', 'not in'):
                parts.append(f"{field} {op} {value!r}")
            elif op in _OP_MAP:
                parts.append(f"{field} {_OP_MAP[op]} {value!r}")
        return ' and '.join(parts) if parts else None
    except Exception as e:
        _logger.warning("Domain to py_expr conversion error: %s", e)
        return None


class BaseFieldAccessPatch(models.AbstractModel):
    _inherit = 'base'

    # ----- Helper: user üçün aktiv qaydaları tap -----
    def _get_field_access_rules(self):
        user = self.env.user
        if user._is_superuser():
            return self.env['field.access.line']
        try:
            config = self.env['field.access.config'].sudo().search([
                ('user_id', '=', user.id),
                ('active', '=', True),
            ], limit=1)
            if not config:
                return self.env['field.access.line']
            return config.line_ids.filtered(
                lambda l: l.active and l.model_name == self._name
            )
        except Exception as e:
            _logger.warning("Field access config read error: %s", e)
            return self.env['field.access.line']

    # ----- Cache key: user + config write_date əlavə et -----
    @api.model
    def _get_view_cache_key(self, view_id=None, view_type='form', **options):
        key = super()._get_view_cache_key(view_id=view_id, view_type=view_type, **options)
        config = self.env['field.access.config'].sudo().search([
            ('user_id', '=', self.env.uid),
        ], limit=1)

        line_dates = config.line_ids.mapped('write_date') if config else []
        last_line_date = max(line_dates).isoformat() if line_dates else ''

        config_key = (
            self.env.uid,
            config.id if config else 0,
            config.active if config else False,
            config.write_date.isoformat() if config and config.write_date else '',
            last_line_date,
        )
        return key + config_key

    # ----- fields_get -----
    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields=allfields, attributes=attributes)
        rules = self._get_field_access_rules()
        if not rules:
            return res

        for rule in rules.filtered(lambda r: r.condition_type == 'always'):
            fname = rule.field_name
            if fname not in res:
                continue
            if rule.action == 'hide':
                res[fname]['invisible'] = True
                res[fname]['searchable'] = False
                res[fname]['exportable'] = False
            elif rule.action == 'readonly':
                res[fname]['readonly'] = True
            elif rule.action == 'required':
                res[fname]['required'] = True
        return res

    # ----- read -----
    def read(self, fields=None, load='_classic_read'):
        records = super().read(fields=fields, load=load)
        rules = self._get_field_access_rules()
        if not rules or not records:
            return records

        for rec_dict in records:
            rec_id = rec_dict.get('id')
            if not rec_id:
                continue
            record = self.browse(rec_id)
            for rule in rules:
                if not rule._evaluate(record):
                    continue
                fname = rule.field_name
                if fname not in rec_dict:
                    continue
                if rule.action == 'hide':
                    rec_dict[fname] = False
                elif rule.action == 'mask':
                    rec_dict[fname] = rule.mask_value or '***'
        return records

    # ----- write -----
    def write(self, vals):
        rules = self._get_field_access_rules()
        if rules:
            for record in self:
                for rule in rules:
                    if not rule._evaluate(record):
                        continue
                    fname = rule.field_name
                    if rule.action == 'readonly' and fname in vals:
                        raise ValidationError(
                            f"'{fname}' sahəsi sizin üçün yalnız oxu rejimindədir."
                        )
                    if rule.action == 'required':
                        new_val = vals.get(fname, record[fname] if fname in record._fields else None)
                        if not new_val:
                            raise ValidationError(
                                f"'{fname}' sahəsi sizin üçün məcburidir."
                            )
        return super().write(vals)

    # ----- create -----
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        rules = self._get_field_access_rules()
        if rules:
            for record in records:
                for rule in rules:
                    if rule.action != 'required':
                        continue
                    if not rule._evaluate(record):
                        continue
                    fname = rule.field_name
                    if fname in record._fields and not record[fname]:
                        raise ValidationError(
                            f"'{fname}' sahəsi sizin üçün məcburidir."
                        )
        return records

    # ----- _get_view: form/list XML-ə atribut qoy -----
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        rules = self._get_field_access_rules()
        if not rules:
            return arch, view

        always_rules = rules.filtered(lambda r: r.condition_type == 'always')
        for rule in always_rules:
            fname = rule.field_name
            for node in arch.xpath(f"//field[@name='{fname}']"):
                if rule.action == 'hide':
                    node.set('invisible', '1')
                    node.set('column_invisible', '1')
                elif rule.action == 'readonly':
                    node.set('readonly', '1')
                elif rule.action == 'required':
                    node.set('required', '1')

            if rule.action == 'hide':
                for label in arch.xpath(f"//label[@for='{fname}']"):
                    label.set('invisible', '1')
                for node in arch.xpath(f"//field[@name='{fname}']"):
                    node.set('nolabel', '1')

        domain_rules = rules.filtered(lambda r: r.condition_type == 'domain')
        for rule in domain_rules:
            fname = rule.field_name
            py_expr = _domain_to_py_expr(rule.condition_domain)
            if not py_expr:
                continue
            for node in arch.xpath(f"//field[@name='{fname}']"):
                if rule.action == 'hide':
                    node.set('invisible', py_expr)
                    node.set('column_invisible', py_expr)
                elif rule.action == 'readonly':
                    node.set('readonly', py_expr)
                elif rule.action == 'required':
                    node.set('required', py_expr)

            if rule.action == 'hide':
                for label in arch.xpath(f"//label[@for='{fname}']"):
                    label.set('invisible', py_expr)
                for node in arch.xpath(f"//field[@name='{fname}']"):
                    node.set('nolabel', '1')

        return arch, view