# -*- coding: utf-8 -*-
{
    'name': 'Product Stock Locations on Invoice',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Display product stock availability by location with Ctrl+F9 shortcut in invoice lines',
    'description': """
        This module allows users to view product stock availability by location
        by pressing Ctrl+F9 when on a product line in invoices.

        Features:
        - Press Ctrl+F9 on invoice line to see stock by location
        - Uses OWL JS components
        - Shows location, quantity on hand, reserved, and available quantities
    """,
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'stock',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'product_stock_locations/static/src/js/stock_location_dialog.js',
            'product_stock_locations/static/src/js/invoice_line_stock_widget.js',
            'product_stock_locations/static/src/xml/stock_location_dialog.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}