# -*- coding: utf-8 -*-
{
    'name': 'Trail Lesson #Majidov',
    'version': '18.0.1.1.0',
    'summary': 'Manage Trial Lessons for Teachers and Students',
    'description': 'Module to schedule and manage trial lessons with video recording support.',
    'category': 'Education',
    'author': 'Custom',
    'depends': ['base', 'mail', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        # Configurator views (actions must load before menus reference them)
        'views/trail_lesson_config_views.xml',
        'views/trail_lesson_question_views.xml',
        # Main model views
        'views/trail_lesson_views.xml',
        # Wizard views
        'views/trail_lesson_complete_wizard_views.xml',
        'views/trail_lesson_plan_wizard_views.xml',
        # Menus (last — all actions must exist first)
        'views/trail_lesson_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}