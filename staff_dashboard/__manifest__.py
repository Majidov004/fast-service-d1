# -*- coding: utf-8 -*-
{
    'name': 'Staff Dashboard',
    'version': '18.0.1.0.0',
    'category': 'Extra Tools',
    'summary': 'Lesson comments feed + user activity tracking dashboard',
    'author': 'Custom Development',
    'depends': ['base', 'hr', 'lesson_record'],
    'data': [
        'security/dashboard_security.xml',
        'security/ir.model.access.csv',
        'views/dashboard_action.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'staff_dashboard/static/src/css/dashboard.css',
            'staff_dashboard/static/src/xml/dashboard.xml',
            'staff_dashboard/static/src/js/activity_service.js',
            'staff_dashboard/static/src/js/filter_widgets.js',
            'staff_dashboard/static/src/js/dashboard.js',
            'staff_dashboard/static/src/css/analytics_dashboard.css',
            'staff_dashboard/static/src/xml/analytics_dashboard.xml',
            'staff_dashboard/static/src/js/analytics_dashboard.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
