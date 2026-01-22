{
    "name": "Product Stock Ledger - Column Filter",
    "version": "1.0",
    "author": "You",
    "category": "Inventory",
    "summary": "Column filter and reorder for Product Stock Ledger",
    "depends": [
        "web",
        "product_stock_ledger",
    ],
    "data": [
        "views/ledger_view_extension.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "product_stock_ledger_filter/static/src/js/column_filter_component.js",
            "product_stock_ledger_filter/static/src/js/list_controller_patch.js",
            "product_stock_ledger_filter/static/src/js/list_view_extension.js",
            "product_stock_ledger_filter/static/src/xml/column_filter_templates.xml",
            "product_stock_ledger_filter/static/src/css/column_filter_styles.css",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}