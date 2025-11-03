{
    'name': 'Day Book with Analytic Accounts',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Day Book Reports Filtered by Analytic Accounts',
    'description': """
        Extends the Day Book report to filter by analytic accounts.
        Features:
        - Filter by single or multiple analytic accounts
        - Separate reports for each analytic account
        - Combined report showing all analytic accounts
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'om_account_daily_reports',
        'analytic',
        'account'
    ],
    'data': [
        'wizard/daybook_analytic.xml',
        'report/report_daybook_analytic.xml',
        'views/report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}