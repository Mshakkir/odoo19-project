{
    'name': 'Cash Book with Analytic Accounts',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Extend Cash Book Report with Analytic Account Filtering',
    'description': """
        This module extends the Odoo Mates Cash Book report to:
        - Filter by analytic accounts
        - Show separate reports per analytic account
        - Show combined report with analytic account grouping
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'om_account_daily_reports',
        'analytic',
        'account'
    ],
    'data': [
        'wizard/cashbook_analytic.xml',
        'views/report_cashbook_analytic.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}