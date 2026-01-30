{
    'name': 'Invoice Delivery Automation',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Automatically create deliveries from direct customer invoices with warehouse selection',
    'description': """
        This module extends invoice functionality to:
        - Select warehouse per invoice line in direct customer invoices
        - Automatically create separate deliveries for each warehouse when invoice is posted
        - Validate deliveries and link them to invoices
        - Track stock from different warehouses in one invoice
        - Support both invoices created directly and invoices from sale orders
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'account',
        'stock',
        'sale_stock',
    ],
    'data': [
        'Security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}