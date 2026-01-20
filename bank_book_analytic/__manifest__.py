{
    'name': 'Bank Book Report with Analytic Accounts',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Bank Book Report separated by Analytic Accounts',
    'description': """
        This module extends the Bank Book Report from Odoo Mates to support:
        - Separate bank book reports by analytic accounts
        - Combined bank book report (original functionality)
        - Filter by analytic accounts
        - Show details in tree view
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'om_account_daily_reports',
        'analytic',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/account_bankbook_report_views.xml',
        'wizard/account_bankbook_details_views.xml',
        'report/report_bankbook_analytic.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}