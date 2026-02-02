# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order to Product List Link',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Link Purchase Orders to Product List with one click',
    'description': """
        Purchase Order to Product List Link
        ====================================
        This module provides one-click access from Purchase Order lines to product list view.

        Features:
        ---------
        * Click 📋 icon next to products in Purchase Order lines
        * Click 📋 icon next to products in RFQ lines
        * Automatically opens product form/list view for that product
        * Quick access to product details from purchase orders
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'purchase',
        'product',
    ],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}