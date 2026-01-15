# -*- coding: utf-8 -*-
{
    'name': 'Sale Order Date Filter',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Add custom date range filter to sale orders list view',
    'description': """
        Adds a custom date range filter component to sale order list view.
        Built with OWL JS for Odoo 19 CE.
    """,
    'depends': ['sale', 'web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'custom_sale_date_filter/static/src/js/sale_date_filter.js',
            'custom_sale_date_filter/static/src/css/sale_date_filter.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
