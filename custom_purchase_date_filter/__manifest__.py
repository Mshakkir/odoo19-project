# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order & Bill Date Filter',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Add custom date range filter to purchase orders, RFQs and vendor bills list view',
    'description': """
        Adds a custom date range filter component to purchase order, RFQ and vendor bill list views.
        Features:
        - Date range filter (Order Date / Bill Date)
        - Warehouse filter
        - Vendor filter with autocomplete search
        - Purchase Representative/Buyer filter with autocomplete search
        - Reference filters (Order, Vendor, Shipping, Source Document)
        - Amount filter
        - Billing/Payment status filter
        - Delivery note filter
        Built with OWL JS for Odoo 19 CE.
    """,
    'depends': ['purchase', 'account', 'web', 'stock'],
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