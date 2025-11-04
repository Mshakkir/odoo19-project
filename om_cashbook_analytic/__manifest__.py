{
    'name': 'Cashbook Analytic Report',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Cashbook report with Analytic Accounts',
    'author': 'Your Name',
    'depends': ['account', 'om_account_daily_reports', 'analytic'],
    'data': [
        'wizard/cashbook_analytic.xml',
        'report/report_cashbook_analytic.xml',
    ],
    'installable': True,
    'application': False,
}
