{
    'name': 'Custom Accounting Reports',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Custom Balance Sheet and Profit & Loss Reports',
    'description': """
        Enhanced accounting reports with:
        - Separate Balance Sheet and P&L wizards
        - View Details functionality for Balance Sheet
        - Account ledger drill-down
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'account',
        'accounting_pdf_reports',  # Your third-party module
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/financial_report_data.xml',
        'views/account_detail_view.xml',
        'wizard/balance_sheet.xml',
        'wizard/profit_loss.xml',
        'views/menu.xml',
        'views/custom_balance_sheet_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
