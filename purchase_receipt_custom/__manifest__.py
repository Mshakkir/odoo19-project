# -*- coding: utf-8 -*-
{
    'name': 'Purchase Receipt Custom',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Custom purchase receipt enhancements - vendor filter and auto-fill',
    'description': """
        Purchase Receipt Customization
        ================================
        * Filter contact field to show only vendors
        * Filter source document to show only selected vendor's purchase orders
        * Auto-fill product lines when purchase order is selected
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['stock', 'purchase'],
    'data': [
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}