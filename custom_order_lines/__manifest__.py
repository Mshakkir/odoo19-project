#
# {
#     'name': 'Custom Order Lines',
#     'version': '19.0.1.0.0',
#     'category': 'Sales',
#     'summary': 'Customize order lines with SN, product code, and reorganized columns with stock forecast button',
#     'description': """
#         This module customizes the order lines to display:
#         - Serial Number (SN)
#         - Product Code (from product reference)
#         - Reorganized columns with discount calculations
#         - Stock forecast button that turns red when stock is low/unavailable
#         - Hide optional fields (Disc%, Delivery Warehouse, Lead Time, Product Variant)
#         - Applied to Sales Orders, Invoices, and Purchase Orders
#     """,
#     'author': 'Your Company',
#     'website': 'https://www.yourcompany.com',
#     'depends': ['sale_management', 'account_invoice_fixed_discount', 'purchase', 'stock'],
#     'data': [
#         'views/sale_order_views.xml',
#         'views/invoice_views.xml',
#         'views/purchase_order_views.xml',
#     ],
#     'installable': True,
#     'application': False,
#     'auto_install': False,
#     'license': 'LGPL-3',
# }
{
    'name': 'Custom Order Lines',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Customize order lines with SN, product code, stock forecast icon by warehouse',
    'description': """
        This module customizes the order lines to display:
        - Serial Number (SN)
        - Product Code (from product reference)
        - Reorganized columns with discount calculations
        - Stock forecast icon (green = available, red = not available)
          checked against the analytic account's matching warehouse
        - Applied to Sales Orders, Invoices, and Purchase Orders
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['sale_management', 'account_invoice_fixed_discount', 'purchase', 'stock'],
    'data': [
        'views/sale_order_views.xml',
        'views/invoice_views.xml',
        'views/purchase_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_order_lines/static/src/css/stock_icon.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}