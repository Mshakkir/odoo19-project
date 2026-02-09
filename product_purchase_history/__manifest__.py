# -*- coding: utf-8 -*-
{
    'name': 'Product Purchase History on Invoice',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Display product purchase history with Ctrl+F5 shortcut in invoice lines',
    'description': """
        This module allows users to view product purchase history by pressing Ctrl+F5
        when on a product line in sale invoices.

        Features:
        - Press Ctrl+F5 on invoice line to see purchase history
        - Uses OWL JS components
        - Shows supplier, quantity, price, and date information
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'sale',
        'purchase',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'product_purchase_history/static/src/js/purchase_history_dialog.js',
            'product_purchase_history/static/src/js/invoice_line_widget.js',
            'product_purchase_history/static/src/xml/purchase_history_dialog.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}