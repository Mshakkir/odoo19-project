# -*- coding: utf-8 -*-
{
    'name': 'Delivery In/Out Date Filter',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Add custom date range filter to delivery in/out list views',
    'description': """
        Adds a custom date range filter component to delivery in/out list views.
        Features:
        - Date range filter (Scheduled Date)
        - Number/Reference filter
        - Customer filter with autocomplete search
        - Source Location filter
        - Source Document filter
        - Responsible filter with autocomplete search
        - Status filter
        Built with OWL JS for Odoo 19 CE.
    """,
    'depends': ['stock', 'web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'custom_delivery_filter/static/src/js/delivery_filter.js',
            'custom_delivery_filter/static/src/xml/delivery_filter.xml',
            'custom_delivery_filter/static/src/css/delivery_filter.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}