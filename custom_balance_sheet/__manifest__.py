{
    'name': 'Custom Balance Sheet',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Custom Balance Sheet Report',
    'description': 'Adds a Balance Sheet menu under Accounting → Reporting',
    'author': 'Shakkir',
    'depends': ['account'],  # depends on Odoo's account module
    'data': [
        'security/ir.model.access.csv',
        'views/custom_balance_sheet_menu.xml',
        # 'views/balance_sheet_wizard_view.xml',
        'views/balance_sheet_line_view.xml',
    ],
    'installable': True,
    'application': False,
}
