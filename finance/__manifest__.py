# -*- coding: utf-8 -*-
{
    'name': 'Finance #Majidov',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Finance',
    'summary': 'Simple cash management: Cash In / Cash Out, transfers and a dashboard',
    'description': """
        Finance
        =======
        * Cash In / Cash Out documents (draft -> confirmed)
        * Cash registers (each with its own currency)
        * Transfers between cash registers
        * Income / Expense categories with cascading detail (expense item / employee / student / partner)
        * OWL dashboard: per-register cards with period (day/week/month) and trend %
    """,
    'author': 'Majidov',
    'depends': ['base', 'mail', 'hr', 'contact_customization'],
    'data': [
        'security/finance_security.xml',
        'security/ir.model.access.csv',
        'data/finance_sequence.xml',
        'data/finance_data.xml',
        'data/finance_cron.xml',
        'views/finance_cash_register_views.xml',
        'views/finance_payment_method_views.xml',
        'views/finance_expense_views.xml',
        'views/finance_category_views.xml',
        'views/finance_currency_views.xml',
        'views/finance_cash_move_views.xml',
        'views/finance_transfer_views.xml',
        'views/finance_student_charge_views.xml',
        'views/finance_payment_promise_views.xml',
        'views/applicant_paid_wizard_views.xml',
        'views/trail_lesson_complete_wizard_views.xml',
        'views/res_config_settings_views.xml',
        'views/finance_dashboard_action.xml',
        'views/finance_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'finance/static/src/css/finance_dashboard.css',
            'finance/static/src/xml/finance_dashboard.xml',
            'finance/static/src/xml/operations_report.xml',
            'finance/static/src/xml/customer_report.xml',
            'finance/static/src/js/finance_filters.js',
            'finance/static/src/js/finance_dashboard.js',
            'finance/static/src/js/operations_report.js',
            'finance/static/src/js/customer_report.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
