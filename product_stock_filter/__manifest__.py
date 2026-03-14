{
    'name': 'Product Stock Filter Bar',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Add a smart filter bar to Inventory Product list view',
    'description': 'Adds a filter bar above the product list in Inventory with product search, stock status, on-hand quantity, product type, and price range filters.',
    'depends': ['stock', 'web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'product_stock_filter/static/src/xml/product_stock_filter.xml',
            'product_stock_filter/static/src/css/product_stock_filter.css',
            'product_stock_filter/static/src/js/product_stock_filter.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
