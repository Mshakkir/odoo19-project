{
    'name': 'Invoice Stock Automation (Sales & Purchase)',
    'version': '19.0.2.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Auto-create deliveries from customer invoices and receipts from vendor bills with warehouse selection',
    'description': """
        This module extends invoice functionality to:

        CUSTOMER INVOICES (Sales):
        - Select warehouse per invoice line in direct customer invoices
        - Automatically create separate delivery orders for each warehouse when invoice is posted
        - Validate deliveries and link them to invoices

        VENDOR BILLS (Purchase):
        - Select warehouse per bill line in direct vendor bills
        - Automatically create separate receipts for each warehouse when bill is posted
        - Validate receipts and link them to bills

        FEATURES:
        - Track stock from different warehouses in one invoice/bill
        - Support both invoices/bills created directly and those from orders
        - Configurable auto-validation and stock checking
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'account',
        'stock',
        'sale_stock',
        'purchase_stock',
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