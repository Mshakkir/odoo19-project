# -*- coding: utf-8 -*-
{
    'name': 'RFQ & Quotation Date Filter',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Add custom date range filter to RFQ and quotations list view',
    'description': """
        Adds a custom date range filter component to RFQ and quotation list views.
        Features:
        - Date range filter (Order Date)
        - Warehouse filter
        - Vendor filter with autocomplete search
        - Purchase Representative filter with autocomplete search
        - Order Reference filter
        - Vendor Reference filter
        - Status filter
        Built with OWL JS for Odoo 19 CE.
    """,
    'depends': ['purchase', 'purchase_stock', 'web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'custom_rfq_date_filter/static/src/js/rfq_date_filter.js',
            'custom_rfq_date_filter/static/src/xml/rfq_date_filter.xml',
            'custom_rfq_date_filter/static/src/css/rfq_date_filter.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}