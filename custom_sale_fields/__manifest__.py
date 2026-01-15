# {
#     'name': 'Custom Sale Order & Invoice Fields',
#     'version': '19.0.1.0.0',
#     'category': 'Sales/Accounting',
#     'summary': 'Add Customer Reference and AWB/Delivery Note fields to Sale Orders and Invoices',
#     'description': """
#         This module adds:
#         - Customer Reference and AWB Number fields to Sale Orders (below Payment Terms)
#         - Customer Reference and Delivery Note Number fields to Invoices (below Payment Terms)
#         - Auto-transfer of Customer Reference from Sale Order to Invoice
#     """,
#     'author': 'Your Company',
#     'website': 'https://www.yourcompany.com',
#     'depends': ['sale_management', 'account'],
#     'data': [
#         'views/templates.xml',
#         'views/account_move_views.xml',
#     ],
#     'installable': True,
#     'application': False,
#     'auto_install': False,
#     'license': 'LGPL-3',
# }

{
    'name': 'Custom Sale Order & Invoice Fields',
    'version': '19.0.1.0.0',
    'category': 'Sales/Accounting',
    'summary': 'Add Customer Reference and AWB/Delivery Note fields to Sale Orders and Invoices',
    'description': """
        This module adds:
        - PO Number (ref) and AWB Number fields to Sale Orders
        - PO Number (ref), Delivery Note Number, and AWB Number fields to Invoices
        - Auto-transfer of PO Number, AWB Number from Sale Order to Invoice
        - Auto-transfer of Delivery Note Number from Delivery Order to Invoice
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['sale_management', 'account', 'stock', 'sale_stock'],
    'data': [
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',
        'views/account_move_views.xml',
        'views/direct_invoice_menu.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
