{
    "name": "Invoice Discount and Freight",
    "version": "1.0",
    "category": "Accounting",
    "summary": "Add discount and freight to invoices",
    "author": "Your Name",
    "depends": ["sale_management", "account"],
    "data": [
        # "views/sale_order_views.xml",
        # "views/account_move_views.xml",
        "views/report_invoice_templates.xml",
    ],
    "installable": True,
    "application": False,
}
