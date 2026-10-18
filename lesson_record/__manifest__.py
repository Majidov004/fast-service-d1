{
    'name': 'Lesson Record #Majidov',
    'version': '18.0.1.0.0',
    'category': 'Education',
    'summary': 'Manage lesson records and student attendance',
    'description': """
        Lesson Record Management
        ========================
        * Track individual lessons
        * Record student attendance
        * Add teacher comments
        * Mark lessons as completed
    """,
    'author': 'Majidov',
    'depends': ['base', 'training_management'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/lesson_cron.xml', 
        'views/lesson_record_views.xml',
        'views/lesson_menu.xml',
        'views/lesson_homework_wizard_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
