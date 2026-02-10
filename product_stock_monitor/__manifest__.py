# -*- coding: utf-8 -*-
{
    'name': 'Product Stock Monitor',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Display product stock across warehouses with Ctrl+F7 shortcut',
    'description': """
        This module allows users to view product stock across all warehouses by pressing Ctrl+F7.

        Features:
        - Press Ctrl+F7 on product line to see stock monitor
        - Shows stock quantity per warehouse
        - Displays purchase rate and sales rate
        - Works in invoice and product forms
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'stock',
        'product',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        # 'views/stock_monitor_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'product_stock_monitor/static/src/js/stock_monitor_dialog.js',
            'product_stock_monitor/static/src/js/stock_monitor_widget.js',
            'product_stock_monitor/static/src/xml/stock_monitor_dialog.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}