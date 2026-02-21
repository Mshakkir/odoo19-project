{
    'name': 'Product Stock Ledger Filter',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Custom OWL filter bar for Product Stock Ledger list view',
    'description': """
        Adds a sticky filter bar above the Product Stock Ledger list with:
        - Product name/code text search
        - Warehouse dropdown
        - Date range (from / to)
        - Voucher text search
        - Move Type dropdown (IN / OUT / INT)
        - Invoice Status dropdown
        - Apply button  — also triggered by Enter key
        - Clear button  — also triggered by Esc key
    """,
    'author': 'Custom',
    'depends': ['product_stock_ledger', 'web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'product_stock_ledger_filter/static/src/css/filter_bar.css',
            'product_stock_ledger_filter/static/src/components/StockLedgerFilterBar.xml',
            'product_stock_ledger_filter/static/src/components/StockLedgerFilterBar.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
