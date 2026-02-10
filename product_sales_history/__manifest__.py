# -*- coding: utf-8 -*-
{
    'name': 'Product Sales History on Invoice',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Display product sales history with Ctrl+F6 shortcut in invoice lines',
    'description': """
        This module allows users to view product sales history by pressing Ctrl+F6
        when on a product line in invoices.

        Features:
        - Press Ctrl+F6 on invoice line to see sales history
        - Uses OWL JS components
        - Shows customer, quantity, price, and date information
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'sale',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        # 'views/account_move_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'product_sales_history/static/src/js/sales_history_dialog.js',
            'product_sales_history/static/src/js/invoice_line_widget.js',
            'product_sales_history/static/src/xml/sales_history_dialog.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}