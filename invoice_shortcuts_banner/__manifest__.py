# -*- coding: utf-8 -*-
{
    'name': 'Invoice Shortcuts Info Banner',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Display keyboard shortcuts banner in invoice form',
    'description': """
        This module displays an informative banner at the top of invoice forms
        showing available keyboard shortcuts for product history features.

        Displays:
        - Ctrl+F5: Purchase History
        - Ctrl+F6: Sales History
        - Ctrl+F7: Stock Monitor
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
    ],
    'data': [
        'views/account_move_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'invoice_shortcuts_banner/static/src/css/shortcuts_banner.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}