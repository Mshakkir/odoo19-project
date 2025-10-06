{
    "name": "RFQ Product Line History",
    "version": "19.0.1.0.0",
    "category": "Purchases",
    "summary": "Show stock, purchase, and sales history on PO/RFQ product line",
    "author": "Your Name",
    "depends": ["purchase", "sale", "stock"],
    "data": [
        "views/purchase_order_line_views.xml",
        "views/product_history_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}
