{
    'name': 'Hide Cost Fields from Specific Users',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Hide cost and/or sales price fields from specific user groups',
    'description': """
        This module hides the Cost and/or Sales Price fields
        in the product form and list view from users who belong
        to the respective restricted groups:
          - 'Cannot See Cost Price'       → hides Cost, Total Cost Price
          - 'Cannot See Sales Price'      → hides Sales Price, Total Sales Price
    """,
    'author': 'Your Company',
    'depends': ['product', 'stock', 'warehouse_stock_column'],
    'data': [
        'security/hide_cost_security.xml',
        'views/product_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}