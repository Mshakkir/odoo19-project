{
    'name': 'Product Location Column',
    'version': '19.0.2.0.0',
    'category': 'Inventory',
    'summary': 'Add warehouse location columns to product list',
    'description': 'Shows on-hand quantity for WH/Stock, DW/Stock, Balad/Stock',
    'author': 'Your Company',
    'depends': ['stock'],
    'data': [
        'views/product_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}