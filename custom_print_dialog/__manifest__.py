{
    'name': 'Custom Print Dialog',
    'version': '19.0.2.0.0',
    'summary': 'Replace Print button with a split-screen preview dialog (Invoices + Sale Orders)',
    'author': 'Custom',
    'category': 'Accounting/Sales',
    'depends': ['account', 'sale'],
    'data': [
        'views/account_move_views.xml',
        'views/sale_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_print_dialog/static/src/css/print_dialog.css',
            'custom_print_dialog/static/src/xml/print_dialog.xml',
            'custom_print_dialog/static/src/js/print_dialog.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
