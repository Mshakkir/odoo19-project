{
    'name': 'Custom BS & P&L Reports',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Separate ledger details for Balance Sheet and P&L in Odoo CE',
    'depends': ['account'],
    'data': [
        'views/balance_sheet_wizard_views.xml',
        'views/menu_items.xml',
    ],
    'installable': True,
    'auto_install': False,
}
