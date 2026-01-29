# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order Merge Bills',
    'version': '19.0.1.0.0',
    'category': 'Purchases',
    'summary': 'Merge multiple purchase orders from same vendor into one bill',
    'description': """
        This module allows you to select multiple purchase orders from the same vendor
        and merge them into a single vendor bill.

        Features:
        - Merge multiple POs from same vendor
        - Accessible from Actions menu in Purchase Orders list
        - Validates that all selected POs are from the same vendor
        - Creates a single bill with all order lines
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['purchase'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/purchase_order_merge_wizard_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}