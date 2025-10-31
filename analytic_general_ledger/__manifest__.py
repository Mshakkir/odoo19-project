{
    'name': 'Analytic Based General Ledger',
    'version': '1.0',
    'depends': ['accounting_pdf_reports', 'analytic'],
    'author': 'Your Name',
    'category': 'Accounting',
    'summary': 'General Ledger filtered by Analytic Accounts',
    'description': 'Adds analytic account filter and column in General Ledger report.',
    'data': [
        'views/general_ledger_analytic_view.xml',
        'views/move_line_tree_view.xml',
        'views/account_move_line_view.xml',
        'report/report_general_ledger_analytic.xml',
    ],
    'installable': True,
    'application': False,
}
