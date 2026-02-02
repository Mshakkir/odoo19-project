# -*- coding: utf-8 -*-
{
    'name': 'Internal Transfer to Product List Link',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Link Internal Transfer lines to Product List with one click',
    'description': """
        Internal Transfer to Product List Link
        =======================================
        This module provides one-click access from Internal Transfer lines to product list view.

        Features:
        ---------
        * Click 📋 icon next to products in Internal Transfer lines
        * Click 📋 icon next to products in Receipt/Delivery lines
        * Automatically opens product form/list view for that product
        * Quick access to product details from stock transfers
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'stock',
        'product',
    ],
    'data': [
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}