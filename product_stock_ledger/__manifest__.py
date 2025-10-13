# product_stock_ledger/__manifest__.py
{
    "name": "Product Stock Ledger (Custom)",
    "version": "1.0",
    "author": "You",
    "category": "Inventory",
    "summary": "Product wise stock ledger report (QWeb/PDF)",
    "depends": ["stock", "product", "account"],  # add modules you need
    "data": [
        "views/stock_ledger_wizard_views.xml",
        "views/report_action.xml",
        "report/product_stock_ledger_templates.xml",
        "views/assets.xml",
    ],
    "installable": True,
    "application": False,
}
