{
    'name': 'Product Stock Ledger Filter',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Filter bar for Product Stock Ledger list view',
    'depends': ['web', 'product_stock_ledger'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'product_stock_ledger_filter/static/src/css/filter_bar.css',
            'product_stock_ledger_filter/static/src/js/filter_bar.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
