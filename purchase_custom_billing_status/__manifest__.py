{
    'name': 'Custom Billing Status',
    'version': '1.0',
    'category': 'Purchases',
    'sequence': 1,
    'summary': 'Add custom billing status names for purchase orders',
    'description': """
        This module customizes the billing status display for purchase orders:
        - invoiced → Fully Billed
        - to invoice → Waiting Bills
        - partially_invoice → Partially Billed
    """,
    'author': 'Your Company',
    'website': 'https://yourcompany.com',
    'depends': ['purchase'],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
}