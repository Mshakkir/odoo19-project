{
    'name': 'Custom BS & PL Reports',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Separate ledger details for Balance Sheet and P&L using same wizard',
    'depends': ['om_account_accounting', 'account'],
    'data': [
        'views/accounting_report_ext_views.xml',
        'views/menu_items.xml',
    ],
    'installable': True,
    'auto_install': False,
}
