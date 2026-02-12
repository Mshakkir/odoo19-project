# -*- coding: utf-8 -*-
{
    'name': 'Customer Advance Receipt Report',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Add Customer Advance Receipt Report under Customers menu',
    'description': """
        This module adds a Customer Advance Receipt Report wizard under the Customers menu in Accounting.
        Features:
        - Date range filter
        - Journal filter (Bank/Cash)
        - Customer filter
        - List view report displaying customer advance receipt details
        - Uses checkbox to identify advance receipts
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/customer_advance_receipt_wizard_view.xml',
        'views/customer_advance_receipt_view.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
