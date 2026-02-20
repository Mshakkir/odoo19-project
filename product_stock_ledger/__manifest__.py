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
        "views/stock_ledger_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}