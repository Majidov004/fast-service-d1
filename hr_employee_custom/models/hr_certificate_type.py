# -*- coding: utf-8 -*-
from odoo import models, fields


class HrCertificateType(models.Model):
    """Sertifikat növü lookup-u (IELTS, TOEFL, CELTA, …). OWL widget seçim
    siyahısında olmayanı dərhal yarada bilir."""
    _name = 'hr.certificate.type'
    _description = 'Certificate Type'
    _order = 'name'

    name = fields.Char(string='Certificate', required=True)
    active = fields.Boolean(default=True)
