{
    'name': 'Product Stock Ledger',
    'version': '19.0.2.0.0',
    'category': 'Inventory',
    'summary': 'Stock Ledger with built-in filter bar',
    'depends': ['stock', 'purchase', 'sale_management', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_stock_ledger_views.xml',
        'views/product_stock_ledger_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'product_stock_ledger_v2/static/src/css/filter_bar.css',
            'product_stock_ledger_v2/static/src/xml/filter_bar.xml',
            'product_stock_ledger_v2/static/src/js/filter_bar.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
