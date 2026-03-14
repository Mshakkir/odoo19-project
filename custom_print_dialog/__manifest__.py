{
    'name': 'Custom Print Dialog',
    'version': '19.0.3.0.0',
    'summary': 'Replace Print button with a split-screen preview dialog (Invoices, Sale Orders, Purchase Orders)',
    'author': 'Custom',
    'category': 'Accounting/Sales/Purchase',
    'depends': ['account', 'sale', 'purchase','stock'],
    'data': [
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/stock_picking_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js',
            'custom_print_dialog/static/src/scss/print_dialog.scss',
            'custom_print_dialog/static/src/xml/print_dialog.xml',
            'custom_print_dialog/static/src/js/print_dialog.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
