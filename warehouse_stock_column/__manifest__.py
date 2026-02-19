{
    'name': 'Product Location Column',
    'version': '19.0.3.0.0',
    'category': 'Inventory',
    'summary': 'Add warehouse location columns + stock filter bar to product list',
    'depends': ['stock', 'web'],
    'data': [
        'views/product_template.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'warehouse_stock_column/static/src/css/stock_filter_bar.css',
            'warehouse_stock_column/static/src/components/product_stock_filter.js',
            'warehouse_stock_column/static/src/components/product_stock_filter.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}