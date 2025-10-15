{
    "name": "Product Stock Ledger (Custom)",
    "version": "1.0",
    "author": "You",
    "category": "Inventory",
    "summary": "Product-wise stock ledger report with Purchase, Sales & Delivery Details",
    "depends": [
        "stock",
        "product",
        "account",
        "web",
        "purchase",          # For purchase order and vendor-related details
        "sale_management",   # For sales order and delivery note details
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/ledger_line_views.xml",
        "views/stock_ledger_wizard_views.xml",
        "views/report_action.xml",
        "report/product_stock_ledger_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "product_stock_ledger/static/src/js/ledger_list_footer.js",
        ],
        "web.report_assets_common": [
            "product_stock_ledger/static/src/css/report_styles.css",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
