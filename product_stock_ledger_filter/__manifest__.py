# -*- coding: utf-8 -*-
{
    'name': 'Product Stock Ledger - Column Filter',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Add column filter bar to Product Stock Ledger list view',
    'depends': ['web', 'product_stock_ledger'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'product_stock_ledger_filter/static/src/js/ledger_column_filter.js',
            'product_stock_ledger_filter/static/src/css/ledger_column_filter.css',
            # NOTE: No XML template file — the filter bar is pure DOM injection,
            # no OWL component template is needed. Loading an unused OWL template
            # causes "this.child.mount is not a function" in Odoo 19.
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}








# # -*- coding: utf-8 -*-
# {
#     'name': 'Product Stock Ledger - Column Filter',
#     'version': '19.0.1.0.0',
#     'category': 'Inventory',
#     'summary': 'Add column filter and visibility toggle to Product Stock Ledger list view',
#     'description': """
#         Adds a column filter component to the Product Stock Ledger list view.
#         Features:
#         - Show/Hide individual columns
#         - Reorder columns (move up/down)
#         - Search columns
#         - Show All / Hide All buttons
#         - Reset to default
#         - Persistent storage of preferences
#         Built with OWL JS for Odoo 19 CE.
#     """,
#     'depends': ['web', 'product_stock_ledger'],
#     'data': [],
#     'assets': {
#         'web.assets_backend': [
#             'product_stock_ledger_filter/static/src/js/ledger_column_filter.js',
#             'product_stock_ledger_filter/static/src/xml/ledger_column_filter.xml',
#             'product_stock_ledger_filter/static/src/css/ledger_column_filter.css',
#         ],
#     },
#     'installable': True,
#     'application': False,
#     'auto_install': False,
#     'license': 'LGPL-3',
# }