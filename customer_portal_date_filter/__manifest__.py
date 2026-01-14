# -*- coding: utf-8 -*-
{
    "name": "Backend Date Range Filter",
    "version": "19.0.1.0.0",
    "category": "Tools",
    "sequence": 100,
    "summary": "Add date range filter inputs to backend list views",
    "description": """
Backend Date Range Filter
=========================

Adds date range input boxes to Odoo backend list views for easy filtering.

Features:
---------
* Date input boxes in search bar (From Date & To Date)
* Works on Sale Orders
* Works on Invoices/Bills
* Quick filter buttons (Today, This Week, This Month, etc.)
* No JavaScript required - uses native Odoo search
* Native browser date picker
* Easy to extend to other models

Usage:
------
After installation, go to:
- Sales → Orders → See date input boxes in search bar
- Accounting → Invoices → See date input boxes in search bar

Simply select dates and results will be filtered automatically!
    """,
    "author": "Your Company Name",
    "website": "https://www.yourcompany.com",
    "license": "LGPL-3",

    # Dependencies
    "depends": [
        "sale_management",  # For sale orders
        "account",  # For invoices/bills
    ],

    # Data files
    "data": [
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
    ],

    # No assets section = No CSS file needed

    # Module information
    "installable": True,
    "auto_install": False,
    "application": False,
}