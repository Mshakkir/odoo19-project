{
    'name': 'Invoice Date Range Filter',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Add From Date and To Date filters in invoice list view header',
    'description': """
        This module safely adds date range filters in the invoice list view header.

        Features:
        - Date filters in the list view header (toolbar area)
        - Safe JavaScript with error handling
        - Easy to uninstall - no UI breaking
        - Only affects invoice list views
        - No modifications to core Odoo files
    """,
    'author': 'Your Company',
    'depends': ['account'],
    'data': [
        'views/account_move_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_invoice_date_filter/static/src/js/invoice_date_filter.js',
            'custom_invoice_date_filter/static/src/xml/invoice_date_filter.xml',
            'custom_invoice_date_filter/static/src/css/invoice_date_filter.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}