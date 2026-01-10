# -*- coding: utf-8 -*-
{
    'name': 'Custom Invoice List View',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Customize invoice list view with additional fields',
    'description': """
        Customizes the invoice list view to display:
        - Invoice Date
        - Invoice Number
        - Customer
        - Warehouse
        - Reference
        - Tax Excluded Amount
        - Tax Amount
        - Total Amount
        - Amount Due
        - Salesperson
        - Shipping Reference
        - Delivery Note Number
    """,
    'depends': ['account', 'stock', 'sale'],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}