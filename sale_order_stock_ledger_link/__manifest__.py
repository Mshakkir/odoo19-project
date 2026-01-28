# -*- coding: utf-8 -*-
{
    'name': 'Sales Order to Product Stock Ledger Link',
    'version': '19.0.1.0.2',
    'category': 'Sales',
    'summary': 'Link Sales Order lines to Product Stock Ledger with one click',
    'description': """
        Sales Order to Product Stock Ledger Link
        =========================================
        This module integrates with the Product Stock Ledger (Custom) module
        to provide one-click access from Sales Order lines to detailed stock ledger.

        Features:
        ---------
        * Click 📊 icon next to products in Sales Order lines
        * Click 📊 icon next to products in Customer Invoices/Vendor Bills
        * Automatically generates and displays stock ledger for that product
        * Shows receipts, deliveries, rates, balance, and invoice status
        * Seamlessly integrates with your custom stock ledger module
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'sale',
        'stock',
        'account',
        'product_stock_ledger',  # Your custom stock ledger module
    ],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}