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
        - Warehouse (computed from PO/GR)
        - Reference
        - Tax Excluded Amount
        - Tax Amount
        - Total Amount
        - Amount Due
        - Purchase Representative
        - Shipping Reference (AWB Number)
        - Delivery Note Number (Goods Receipt)
        - PO Number

        Note: This module works with existing PO Number, Goods Receipt, 
        and AWB Number fields in your system.
    """,
    'depends': ['account', 'stock', 'purchase', 'purchase_stock','purchase_bill_form_modified'],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}