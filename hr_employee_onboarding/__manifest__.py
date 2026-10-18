# -*- coding: utf-8 -*-
{
    'name': 'HR Employee Onboarding Invite #Majidov',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Send login credentials to new users and redirect them to their employee form on first login.',
    'author': 'Custom',
    'depends': ['base', 'hr', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template.xml',
        'views/res_users_views.xml',
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
