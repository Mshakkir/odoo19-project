{
    'name': 'Hide Cost Fields from Specific Users',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Hide cost and total cost price fields from specific user groups',
    'description': """
        This module hides the Cost and Total Cost Price fields
        in the product form and list view from users who belong
        to the 'Cannot See Cost' group.
    """,
    'author': 'SSAOCO',
    'depends': ['product', 'stock', 'warehouse_stock_column'],
    'data': [
        'security/hide_cost_security.xml',
        'views/product_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}