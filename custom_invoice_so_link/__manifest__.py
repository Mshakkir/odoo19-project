# {
#     'name': 'Invoice Sales Order Link',
#     'version': '19.0.1.0.0',
#     'category': 'Accounting',
#     'summary': 'Link invoices to sales orders with customer filtering',
#     'depends': ['sale_management', 'account'],  # adjust 'account' if using odoo mates module
#     'data': [
#         'security/ir.model.access.csv',
#         'views/account_move_views.xml',
#
#     ],
#     'installable': True,
#     'application': False,
#     'auto_install': False,
# }
{
    'name': 'Invoice Sales Order Link - Enhanced',
    'version': '19.0.3.0.0',
    'category': 'Accounting',
    'summary': 'Link invoices to sales orders with multi-order invoicing',
    'description': """
        Enhanced Invoice Sales Order Link Module
        ==========================================

        Features:
        ---------
        * Link single sale order to invoice
        * Create combined invoice from multiple sale orders
        * Select multiple sale orders with checkboxes
        * Automatically merge invoice lines from selected orders
        * Customer filtering and validation
        * Compatible with Odoo 19 CE and Odoo Mates accounting module

        Usage:
        ------
        1. Single Invoice: Open invoice and select a sale order from dropdown
        2. Multi Invoice: Select multiple sale orders in list view and click 
           "Action > Create Combined Invoice"
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'sale_management',
        'account',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/sale_order_views.xml',
        'wizard/multi_sale_invoice_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}