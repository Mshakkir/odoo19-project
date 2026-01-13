{
    'name': 'Invoice Warehouse & Customer Filters',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Add warehouse and customer filter buttons to invoice list',
    'description': """
Invoice Warehouse & Customer Filters
=====================================

This module adds convenient filtering options to the sales invoice list:

Features:
---------
* Warehouse column in invoice list view
* Quick filter buttons for warehouses at the bottom of search panel
* Quick filter buttons for customers at the bottom of search panel
* Group by Warehouse option
* Group by Customer option
* Easy one-click filtering for Dammam, Main, and other warehouses
* Easy one-click filtering for Customer 1, 2, 3, 4, etc.

Usage:
------
1. Go to Sales → Invoices
2. Click on the search icon
3. Scroll down to see filter sections
4. Click on warehouse or customer filters to instantly filter the list

    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'account',
        'sale',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}