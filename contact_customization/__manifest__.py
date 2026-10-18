# -*- coding: utf-8 -*-
{
    'name': 'Contact Customization #Majidov',
    'version': '18.0.1.0.0',
    'category': 'Contacts',
    'summary': 'Applicant & Student contact management with trial lesson assessment',
    'author': 'Custom Development',
    'depends': ['base', 'contacts', 'hr', 'trail_lesson', 'lesson_record'],
    'data': [
        'security/ir.model.access.csv',
        'views/planned_remember_wizard_view.xml',
        'views/res_partner_form_view.xml',
        'views/res_partner_filter_view.xml',
        'views/applicant_views.xml',
        'views/student_views.xml',
        'views/planned_remember_views.xml',
        'views/waiting_student_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'contact_customization/static/src/css/meeting_comments.css',
            'contact_customization/static/src/xml/meeting_comments_widget.xml',
            'contact_customization/static/src/js/meeting_comments_widget.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
