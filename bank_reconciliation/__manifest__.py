# # -*- coding: utf-8 -*-
# {
#     'name': 'Manual Bank Reconciliation',
#     'version': '19.0.1.0.0',
#     'author': 'Cybrosys Techno Solutions',
#     'company': 'Cybrosys Techno Solutions',
#     'website': 'https://www.cybrosys.com',
#     'category': 'Accounting',
#     'summary': 'Traditional bank statement reconciliation method',
#     'description': """Traditional bank statement reconciliation method for Odoo 19""",
#     'depends': ['account'],
#     'data': [
#         'security/ir.model.access.csv',
#         'data/sequence_data.xml',
#         'views/account_move_line_view.xml',
#         # 'views/account_journal_dashboard_view.xml',
#         'views/bank_statement_wiz_view.xml',
#     ],
#     'assets': {},
#     'images': ['static/description/banner.png'],
#     'license': 'AGPL-3',
#     'installable': True,
#     'auto_install': False,
#     'application': False,
# }
# -*- coding: utf-8 -*-
{
    'name': 'Manual Bank Reconciliation',
    'version': '19.0.1.0.0',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'category': 'Accounting',
    'summary': 'Traditional bank statement reconciliation method with color coding and PDF reports',
    'description': """
        Traditional Bank Statement Reconciliation for Odoo 19
        ======================================================
        * Bank statement reconciliation with color-coded status
        * Mark transactions as cleared/pending/overdue
        * Professional PDF reconciliation reports
        * Dashboard integration
        * Automatic overdue detection
    """,
    'depends': ['account', 'point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/cron_data.xml',
        'views/account_move_line_view.xml',
        'views/account_journal_dashboard_view.xml',
        'views/bank_statement_wiz_view.xml',
        'views/bank_reconciliation_report_template.xml',
    ],
    'assets': {},
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}