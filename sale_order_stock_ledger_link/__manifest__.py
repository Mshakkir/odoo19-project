# -*- coding: utf-8 -*-
{
    'name': 'Sales Order to Stock Ledger Link',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Add clickable link from Sales Order lines to Product Stock Ledger',
    'description': """
        Sales Order to Stock Ledger Link
        =================================
        This module adds the ability to click on products in Sales Order lines
        to navigate directly to the Product Stock Ledger filtered for that product.

        Features:
        ---------
        * Makes product field in SO lines clickable
        * Opens Product Stock Ledger filtered by the selected product
        * Works seamlessly with Odoo 19 CE
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'sale',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}