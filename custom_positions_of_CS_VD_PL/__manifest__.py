{
    'name': 'Partner Ledger in Sales & Purchase',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Add Partner Ledger to Sales and Purchase top bar',
    'depends': ['sale_management', 'purchase', 'om_account_accountant'],  # om_account_accountant is the Odoo Mates module
    'data': [
        'views/partner_ledger_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}