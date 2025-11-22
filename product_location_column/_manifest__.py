# File: product_location_column/__manifest__.py

{
    'name': 'Product Location Column',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Add warehouse location column to product list',
    'description': '''
        This module adds a warehouse location column to the product list view.
        It shows all internal locations where the product has stock.
    ''',
    'author': 'Your Company',
    'website': 'https://yourcompany.com',
    'depends': ['stock'],
    'data': [
        'views/product_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}