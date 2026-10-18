# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.session import Session


class StaffDashboardSession(Session):
    """Standart /web/session/logout-u genişləndirir — çıxışda
    istifadəçinin açıq login sessiyasını bağlayır ki, növbəti giriş
    (cookie/link ilə avtomatik olsa belə) ayrı sessiya kimi qeyd olunsun."""

    @http.route()
    def logout(self, *args, **kw):
        uid = request.session.uid
        if uid:
            try:
                request.env['user.login.log'].sudo().close_session(uid)
            except Exception:
                # logout heç vaxt bu səbəbdən pozulmamalıdır
                pass
        return super().logout(*args, **kw)
