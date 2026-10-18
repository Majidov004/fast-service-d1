from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval
import logging

_logger = logging.getLogger(__name__)


class FieldAccessLine(models.Model):
    _name = 'field.access.line'
    _description = 'Sahə Giriş Qaydası'
    _order = 'sequence, id'

    config_id = fields.Many2one(
        'field.access.config',
        string='Konfiqurasiya',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    # Model və sahə
    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
        ondelete='cascade',
        help='Hansı modelin sahəsi'
    )
    model_name = fields.Char(
        string='Model (texniki)',
        compute='_compute_model_name',
        store=True,
    )

    @api.depends('model_id')
    def _compute_model_name(self):
        for rec in self:
            rec.model_name = rec.model_id.model if rec.model_id else False

    @api.onchange('model_id')
    def _onchange_model_id(self):
        self.condition_domain = '[]'
        self.field_id = False
    field_id = fields.Many2one(
        'ir.model.fields',
        string='Sahə',
        required=True,
        ondelete='cascade',
        domain="[('model_id', '=', model_id)]"
    )
    field_name = fields.Char(related='field_id.name', store=True)

    # Şərt növü
    condition_type = fields.Selection([
        ('always', 'Həmişə'),
        ('domain', 'Domain (filtr)'),
        ('python', 'Python kod'),
    ], string='Şərt növü', default='always', required=True)

    # Domain şərti
    condition_domain = fields.Char(
        string='Domain',
        default='[]',
        help="Nümunə: [('state','=','draft')]"
    )

    # Sahə dəyəri şərti
    trigger_field_id = fields.Many2one(
        'ir.model.fields',
        string='Yoxlanacaq sahə',
        domain="[('model_id', '=', model_id)]",
        help='Hansı sahənin dəyərinə baxılacaq'
    )
    
    operator = fields.Selection([
        ('=', '='),
        ('!=', '!='),
        ('>', '>'),
        ('<', '<'),
        ('>=', '>='),
        ('<=', '<='),
        ('in', 'daxildir'),
        ('not in', 'daxil deyil'),
        ('like', 'oxşardır'),
    ], string='Operator', default='=')
    trigger_value = fields.Char(
        string='Dəyər',
        help='Məsələn: 7, draft, ["draft","sent"]'
    )

    # Python şərti
    condition_python = fields.Text(
        string='Python kod',
        help="record, user, env dəyişənlərindən istifadə et.\nNümunə: result = record.amount > 1000"
    )

    # Hərəkət
    action = fields.Selection([
        ('hide', 'Gizlət'),
        ('readonly', 'Yalnız oxu'),
        ('required', 'Məcburi et'),
        ('mask', 'Maskala (***)'),
    ], string='Hərəkət', required=True, default='hide')

    mask_value = fields.Char(
        string='Maska dəyəri',
        default='***',
        help='Maskalama üçün göstəriləcək mətn'
    )

    note = fields.Char(string='Qeyd')

    @api.constrains('condition_python')
    def _check_python(self):
        for rec in self:
            if rec.condition_type == 'python' and not rec.condition_python:
                raise ValidationError(_('Python şərti boş ola bilməz.'))

    # @api.constrains('condition_type', 'trigger_field_id', 'trigger_value')
    # def _check_field_value(self):
    #     for rec in self:
    #         if rec.condition_type == 'field_value':
    #             if not rec.trigger_field_id or not rec.operator:
    #                 raise ValidationError(_('Sahə dəyəri şərti üçün sahə və operator tələb olunur.'))

    def _evaluate(self, record):
        """Bu qayda record üçün aktivdirmi?"""
        self.ensure_one()
        try:
            if self.condition_type == 'always':
                return True

            if self.condition_type == 'domain':
                domain = safe_eval(self.condition_domain or '[]')
                if not domain:
                    return False
                return bool(record.filtered_domain(domain))

            if self.condition_type == 'field_value':
                if not self.trigger_field_id:
                    return False
                fname = self.trigger_field_id.name
                if fname not in record._fields:
                    return False
                val = record[fname]
                try:
                    target = safe_eval(self.trigger_value or 'False')
                except Exception:
                    target = self.trigger_value

                op = self.operator
                if hasattr(val, 'id'):
                    val = val.id
                if op == '=':
                    return val == target
                if op == '!=':
                    return val != target
                if op == '>':
                    return val is not None and val > target
                if op == '<':
                    return val is not None and val < target
                if op == '>=':
                    return val is not None and val >= target
                if op == '<=':
                    return val is not None and val <= target
                if op == 'in':
                    return val in (target or [])
                if op == 'not in':
                    return val not in (target or [])
                if op == 'like':
                    return target and str(target) in str(val or '')
                return False

            if self.condition_type == 'python':
                ctx = {
                    'record': record,
                    'user': self.env.user,
                    'env': self.env,
                    'result': False,
                }
                safe_eval(self.condition_python or '', ctx, mode='exec', nocopy=True)
                return bool(ctx.get('result'))

        except Exception as e:
            _logger.warning("Field access rule %s evaluation error: %s", self.id, e)
            return False
        return False
    
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
