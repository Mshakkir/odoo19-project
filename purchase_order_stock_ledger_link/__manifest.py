# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order to Product Stock Ledger Link',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Link Purchase Orders to Product Stock Ledger with one click',
    'description': """
        Purchase Order to Product Stock Ledger Link
        ============================================
        This module integrates with the Product Stock Ledger (Custom) module
        to provide one-click access from Purchase Order lines to detailed stock ledger.

        Features:
        ---------
        * Click 📊 icon next to products in Purchase Order lines
        * Click 📊 icon next to products in RFQ lines
        * Automatically generates and displays stock ledger for that product
        * Shows receipts, deliveries, rates, balance, and invoice status
        * Seamlessly integrates with your custom stock ledger module
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'purchase',
        'stock',
        'product_stock_ledger',  # Your custom stock ledger module
    ],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}