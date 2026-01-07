{
    'name': 'Custom Sale Order & Invoice Fields',
    'version': '19.0.1.0.0',
    'category': 'Sales/Accounting',
    'summary': 'Add Customer Reference and AWB/Delivery Note fields to Sale Orders and Invoices',
    'description': """
        This module adds:
        - Customer Reference and AWB Number fields to Sale Orders (below Payment Terms)
        - Customer Reference and Delivery Note Number fields to Invoices (below Payment Terms)
        - Auto-transfer of Customer Reference from Sale Order to Invoice
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['sale_management', 'account'],
    'data': [
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
