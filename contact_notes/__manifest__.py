# -*- coding: utf-8 -*-
{
    'name': 'Contact Notes',
    'version': '18.0.1.0.0',
    'category': 'Contacts',
    'summary': 'Add tracked notes to contacts',
    'author': 'Custom Development',
    'depends': ['base', 'contacts', 'hr', 'contact_customization'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/contact_note_wizard_view.xml',
        'views/res_partner_notes_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'contact_notes/static/src/css/contact_notes.css',
            'contact_notes/static/src/xml/contact_notes_widget.xml',
            'contact_notes/static/src/js/contact_notes_widget.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
