# File: product_location_column/__manifest__.py

{
    'name': 'Product Location Column',
    'version': '19.0.2.0.0',
    'category': 'Inventory',
    'summary': 'Add warehouse location columns to product list',
    'description': '''
        This module adds separate warehouse columns to the product list view.
        It shows on-hand quantity for each warehouse:
        - WH/Stock
        - DW/Stock
        - Balad/Stock
    ''',
    'author': 'Your Company',
    'website': 'https://yourcompany.com',
    'depends': ['product', 'stock'],
    'data': [
        'views/product_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}