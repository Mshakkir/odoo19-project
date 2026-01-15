# -*- coding: utf-8 -*-
{
    'name': 'Sale Order & Invoice Date Filter',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Add custom date range filter to sale orders and invoices list view',
    'description': """
        Adds a custom date range filter component to sale order and invoice list views.
        Features:
        - Date range filter (Order Date / Invoice Date)
        - Warehouse filter (Sale Orders only)
        - Customer filter with autocomplete search
        - Salesperson filter with autocomplete search
        Built with OWL JS for Odoo 19 CE.
    """,
    'depends': ['sale', 'account', 'web'],
    'data': [],
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