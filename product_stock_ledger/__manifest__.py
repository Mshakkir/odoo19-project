{
    "name": "Product Stock Ledger (Custom)",
    "version": "1.0",
    "author": "You",
    "category": "Inventory",
    "summary": "Product-wise stock ledger report (QWeb/PDF)",
    "depends": ["stock", "product", "account"],
    "data": [
        "security/ir.model.access.csv",  # <--- added here
        "views/stock_ledger_wizard_views.xml",  # must load before report_action
        "views/stock_move_tree.xml",
        "views/report_action.xml",
        "report/product_stock_ledger_templates.xml",
    ],
    "assets": {
        "web.report_assets_common": [
            "product_stock_ledger/static/src/css/report_styles.css",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
