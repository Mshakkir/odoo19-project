{
    'name': 'Cash Book Report with Analytic Account',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Cash Book Report filtered by Analytic Account',
    'description': """
        Extends Odoo Mates Cash Book Report with Analytic Account filtering
        - Filter cash book entries by analytic account
        - Inherit existing cash book functionality
        - Compatible with Odoo 19 CE
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'om_account_daily_reports',
        'analytic',
        'account'
    ],
    'data': [
        'wizard/account_cashbook_report_analytic_views.xml',
        'report/report_cashbook_analytic.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}