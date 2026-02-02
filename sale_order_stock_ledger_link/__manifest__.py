# -*- coding: utf-8 -*-
{
    'name': 'Sales Order to Product List Link',
    'version': '19.0.1.0.2',
    'category': 'Sales',
    'summary': 'Link Sales Order lines to Product List with one click',
    'description': """
        Sales Order to Product List Link
        =================================
        This module provides one-click access from Sales Order lines to product list view.

        Features:
        ---------
        * Click 📋 icon next to products in Sales Order lines
        * Click 📋 icon next to products in Customer Invoices/Vendor Bills
        * Automatically opens product form/list view for that product
        * Quick access to product details from sales orders and invoices
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'sale',
        'account',
        'product',
    ],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}