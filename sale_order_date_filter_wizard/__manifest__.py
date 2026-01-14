# -*- coding: utf-8 -*-
{
    "name": "Sale Order Date Filter Wizard",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "sequence": 100,
    "summary": "Filter Sale Orders by date range using a wizard popup",
    "description": """
Sale Order Date Filter Wizard
==============================

Adds a button to Sale Orders list that opens a wizard where you can:
* Select Date From
* Select Date To
* View filtered results instantly

Features:
---------
* Easy date range selection with date pickers
* Filter button in Sale Orders list view
* Clean wizard interface
* No JavaScript required
* Works on Odoo 19 CE

Usage:
------
1. Go to Sales → Orders
2. Click "Filter by Date Range" button
3. Select your date range
4. Click "Apply Filter"
5. View filtered results
    """,
    "author": "Your Company Name",
    "website": "https://www.yourcompany.com",
    "license": "LGPL-3",

    # Dependencies
    "depends": [
        "sale_management",
    ],

    # Data files
    "data": [
        "security/ir.model.access.csv",
        "wizard/sale_order_date_filter_wizard_views.xml",
        "views/sale_order_views.xml",
    ],

    # Module information
    "installable": True,
    "auto_install": False,
    "application": False,
}