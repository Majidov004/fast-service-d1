from odoo import models, fields


class AccessStatusValue(models.Model):
    _name = 'access.status.value'
    _description = 'Status Filter Dəyəri'

    line_id = fields.Many2one(
        'access.config.line',
        string='İcazə sətri',
        required=True,
        ondelete='cascade',
        index=True,
    )
    value = fields.Char(
        string='Status Dəyəri',
        required=True,
        help="Selection sahəsinin açar dəyəri (məs. 'draft', 'done', 'planned')",
    )
