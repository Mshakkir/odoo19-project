# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order & Bill Date Filter',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Add custom date range filter to purchase orders and vendor bills list view',
    'description': """
        Adds a custom date range filter component to purchase order and vendor bill list views.
        Features:
        - Date range filter (Order Date / Bill Date)
        - Warehouse filter (Purchase Orders only)
        - Vendor filter with autocomplete search
        - Purchase Representative filter with autocomplete search
        Built with OWL JS for Odoo 19 CE.
    """,
    'depends': ['purchase', 'account', 'web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'custom_purchase_date_filter/static/src/js/purchase_date_filter.js',
            'custom_purchase_date_filter/static/src/xml/purchase_date_filter.xml',
            'custom_purchase_date_filter/static/src/css/purchase_date_filter.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}