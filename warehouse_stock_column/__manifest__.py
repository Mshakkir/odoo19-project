{
    'name': 'Product Location Column',
    'version': '19.0.4.0.0',
    'category': 'Inventory',
    'summary': 'Add warehouse location columns to product list',
    'depends': ['stock'],
    'data': [
        'security/groups.xml',
        'views/product_template.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'product_location_column/static/src/css/product_list.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}