# -*- coding: utf-8 -*-
{
    'name': 'Delivery Notes & Receipts Date Filter',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Add custom date range filter to delivery notes and receipts list view',
    'description': """
        Adds a custom date range filter component to delivery notes and receipts list views.
        Features:
        - Date range filter (Scheduled Date / Date Done)
        - Customer/Supplier filter with autocomplete search
        - Source Location filter
        - Responsible filter with autocomplete search
        - Status filter
        - Source Document filter
        Built with OWL JS for Odoo 19 CE.
    """,
    'depends': ['stock', 'delivery', 'web'],
    'data': [
        # 'views/stock_picking_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'stock_delivery_receipts_filter/static/src/js/stock_delivery_filter.js',
            'stock_delivery_receipts_filter/static/src/xml/stock_delivery_filter.xml',
            'stock_delivery_receipts_filter/static/src/css/stock_delivery_filter.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}