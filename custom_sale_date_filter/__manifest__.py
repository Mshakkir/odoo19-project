{
    'name': 'Sale Order Date Filter',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Add custom date range filter to sale orders',
    'description': """
        This module adds a custom date range filter to the sale order list view
        using OWL JS components.
    """,
    'depends': ['sale', 'web'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_sale_date_filter/static/src/js/sale_date_filter.js',
            'custom_sale_date_filter/static/src/xml/sale_date_filter.xml',
            'custom_sale_date_filter/static/src/css/sale_date_filter.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}