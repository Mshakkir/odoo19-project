{
    'name': 'Delivery Notes Batch Invoicing',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Create invoices from multiple delivery notes',
    'description': """
        This module allows you to:
        - Select multiple delivery notes for the same customer
        - Create invoices in batch from delivery notes
        - Similar to sale order batch invoicing
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['stock', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/stock_picking_invoice_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
