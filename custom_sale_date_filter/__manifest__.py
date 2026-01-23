# # -*- coding: utf-8 -*-
# {
#     'name': 'Sale Order, Quotation & Invoice Date Filter',
#     'version': '19.0.2.0.0',
#     'category': 'Sales',
#     'summary': 'Add custom date range filter to sale orders, quotations, and invoices list view',
#     'description': """
#         Adds a custom date range filter component to sale order, quotation, and invoice list views.
#         Features:
#         - Date range filter (Order Date / Invoice Date)
#         - Warehouse filter (Sale Orders, Quotations, and Invoices)
#         - Customer filter with autocomplete search
#         - Salesperson filter with autocomplete search
#         - Document number filter
#         - Total amount filter
#         - Customer reference filter
#         - PO number filter
#         - Shipping reference filter
#         - Keyboard shortcuts:
#             * Press Enter to apply filters
#             * Press Backspace to clear filters
#         Built with OWL JS for Odoo 19 CE.
#     """,
#     'depends': ['sale', 'account', 'stock', 'web'],
#     'data': [],
#     'assets': {
#         'web.assets_backend': [
#             'custom_sale_date_filter/static/src/js/sale_date_filter.js',
#             'custom_sale_date_filter/static/src/xml/sale_date_filter.xml',
#             'custom_sale_date_filter/static/src/css/sale_date_filter.css',
#         ],
#     },
#     'installable': True,
#     'application': False,
#     'auto_install': False,
#     'license': 'LGPL-3',
# }

# -*- coding: utf-8 -*-
{
    'name': 'Sale Order, Quotation & Invoice Date Filter',
    'version': '19.0.2.0.0',
    'category': 'Sales',
    'summary': 'Add custom date range filter to sale orders, quotations, and invoices list view',
    'description': """
        Adds a custom date range filter component to sale order, quotation, and invoice list views.
        Features:
        - Date range filter (Order Date / Invoice Date)
        - Warehouse filter (Sale Orders, Quotations, and Invoices)
        - Customer filter with autocomplete search
        - Salesperson filter with autocomplete search
        - Document number filter
        - Total amount filter
        - Customer reference filter
        - AWB number filter
        - Delivery Note filter (Invoices only)
        - Keyboard shortcuts: 
            * Press Enter to apply filters
            * Press Escape to clear filters
        Built with OWL JS for Odoo 19 CE.
    """,
    'depends': ['sale', 'account', 'stock', 'web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'custom_sale_date_filter/static/src/css/sale_date_filter.css',
            'custom_sale_date_filter/static/src/js/sale_date_filter.js',
            'custom_sale_date_filter/static/src/xml/sale_date_filter.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}