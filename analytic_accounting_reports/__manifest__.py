{
    'name': 'Analytic Accounting Reports',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Add Analytic Distribution filtering to Balance Sheet and P&L Reports',
    'description': """
        This module extends the accounting PDF reports to include:
        - Analytic distribution (warehouse) filtering
        - Combined and separate warehouse reporting
        - Balance Sheet and P&L with warehouse breakdown
    """,
    'author': 'Your Company',
    'depends': ['accounting_pdf_reports', 'analytic'],
    'data': [
        'wizard/account_report_views.xml',
        'report/report_financial_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}