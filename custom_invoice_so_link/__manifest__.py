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
    'name': 'Invoice Sales Order Link',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Link invoices to sales orders with customer filtering',
    'depends': ['sale_management', 'account'],  # adjust 'account' if using odoo mates module
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}