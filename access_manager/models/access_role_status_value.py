from odoo import models, fields


class AccessRoleStatusValue(models.Model):
    _name = 'access.role.status.value'
    _description = 'Vəzifə Status Filter Dəyəri'

    line_id = fields.Many2one(
        'access.role.line',
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
