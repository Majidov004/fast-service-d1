# -*- coding: utf-8 -*-
{
    'name': 'HR Teacher Profile #Majidov',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Custom fields and form layout for teacher employees',
    'author': 'Custom Development',
    'depends': ['hr', 'hr_skills', 'trail_lesson', 'training_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_employee_custom/static/src/css/employee_table.css',
            'hr_employee_custom/static/src/js/employee_table_widget.js',
            'hr_employee_custom/static/src/xml/employee_table_widget.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}