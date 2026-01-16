{
    'name': 'Custom Sale Order List View',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Customize Sale Order List View Columns',
    'description': """
        This module customizes the sale order list view to reorder columns
        similar to the invoice list view layout.
    """,
    'author': 'Your Company',
    'depends': ['sale_stock', 'sale_management'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}