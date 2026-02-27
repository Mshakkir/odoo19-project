{
    'name': 'Custom Invoice Print Dialog',
    'version': '19.0.1.0.0',
    'summary': 'Replace Print button with a browser-style print dialog with preview',
    'author': 'Custom',
    'category': 'Accounting',
    'depends': ['account'],
    'data': [
        'views/account_move_views.xml',
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
