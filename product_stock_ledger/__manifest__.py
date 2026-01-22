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
        "purchase",
        "sale_management",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_ledger_wizard_views.xml",
        "views/report_action.xml",
        "report/product_stock_ledger_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "product_stock_ledger/static/src/js/stock_ledger_list_controller.js",
            "product_stock_ledger/static/src/xml/stock_ledger_list_view.xml",
            "product_stock_ledger/static/src/css/stock_ledger_filters.css",
        ],
        "web.report_assets_common": [
            "product_stock_ledger/static/src/css/report_styles.css",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}












# {
#     "name": "Product Stock Ledger (Custom)",
#     "version": "1.0",
#     "author": "You",
#     "category": "Inventory",
#     "summary": "Product-wise stock ledger report with Purchase, Sales & Delivery Details",
#     "depends": [
#         "stock",
#         "product",
#         "account",
#         "web",
#         "purchase",          # For purchase order and vendor-related details
#         "sale_management",   # For sales order and delivery note details
#     ],
#     "data": [
#         "security/ir.model.access.csv",
#         "views/stock_ledger_wizard_views.xml",
#         "views/report_action.xml",
#         "report/product_stock_ledger_templates.xml",
#     ],
#     "installable": True,
#     "application": False,
#     "assets": {
#         "web.report_assets_common": [
#             "product_stock_ledger/static/src/css/report_styles.css",
#         ],
#     },
#     "installable": True,
#     "application": False,
#     "license": "LGPL-3",
# }