{
    'name': 'Custom Balance Sheet',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Custom Balance Sheet Report',
    'description': 'Adds a Balance Sheet menu under Accounting → Reporting with details and ledger view.',
    'author': 'Shakkir',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',

        # Views first
        'views/custom_balance_sheet_line_views.xml',
        'views/custom_balance_sheet_menu.xml',

        # Reports last (your folder is named "reports")
        'reports/custom_balance_sheet_report.xml',
        'reports/custom_balance_sheet_report_action.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
