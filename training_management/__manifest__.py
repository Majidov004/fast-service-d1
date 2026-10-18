{
    'name': 'Training Management #Majidov',
    'version': '18.0.1.0.0',
    'category': 'Education',
    'summary': 'Manage training groups, schedules and students',
    'description': """
        Training Management System
        ==========================
        * Create training groups
        * Assign teachers from employees
        * Schedule lessons by day and time
        * Manage students and their lesson counts
    """,
    'depends': ['base', 'hr', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/training_group_views.xml',
        'views/training_group_delete_wizard_views.xml',
        'views/training_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'training_management/static/src/css/meeting_widget.css',
            'training_management/static/src/xml/meeting_widget.xml',
            'training_management/static/src/js/meeting_widget.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}