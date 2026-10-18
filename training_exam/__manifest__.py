{
    'name': 'Training Exam #Majidov',
    'version': '18.0.1.0.0',
    'category': 'Education',
    'summary': 'Exams every 5 lessons for training groups',
    'description': """
        Training Exam
        =============
        * Auto-generates one exam per 5 lessons when a training group starts
        * "Exam" tab on the training group (card style, like the Meeting tab)
        * Per-student result (Weak / Average / Excellent) + comment
        * Exam questions come from the shared Question Bank (trail_lesson),
          filtered by exam number and the group's program
        * Notifies the exam teacher when a 5-lesson block is finished
        * Notifies the teaching teacher about weak results
    """,
    'depends': ['mail', 'trail_lesson', 'training_management', 'lesson_record'],
    'data': [
        'security/ir.model.access.csv',
        'views/training_group_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'training_exam/static/src/css/exam_widget.css',
            'training_exam/static/src/xml/exam_widget.xml',
            'training_exam/static/src/js/exam_widget.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
