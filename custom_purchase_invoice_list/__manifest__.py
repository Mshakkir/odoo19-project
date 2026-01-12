# -*- coding: utf-8 -*-
{
    'name': 'Custom Purchase Invoice List View',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Customize purchase invoice list view with additional fields',
    'description': """
        Customizes the purchase invoice (vendor bill) list view to display:
        - Invoice Date
        - Invoice Number
        - Vendor
        - Warehouse
        - Reference
        - Tax Excluded Amount
        - Tax Amount
        - Total Amount
        - Amount Due
        - Purchase Representative
        - Shipping Reference
        - Delivery Note Number
    """,
    'depends': ['account', 'stock', 'purchase', 'purchase_stock', 'custom_sale_fields'],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}