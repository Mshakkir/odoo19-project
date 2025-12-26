{
    'name': 'Direct Invoice with Stock Move',
    'version': '19.0.1.0.0',
    'category': 'Sales/Accounting',
    'summary': 'Create automatic delivery orders from invoices for counter sales',
    'description': """
        Direct Invoice with Stock Move
        ================================
        This module allows you to create invoices directly for walk-in customers
        and automatically updates inventory by creating and validating delivery orders.

        Features:
        ---------
        * Create invoice directly without sales order
        * Automatic delivery order creation on invoice validation
        * Automatic stock move and inventory update
        * Proper traceability between invoice and delivery
        * Works with stockable products only
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['account', 'stock', 'sale'],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}