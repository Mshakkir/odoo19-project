# -*- coding: utf-8 -*-
{
    'name': 'Payment Form Customization',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Customize Payment Form - Rename Memo and Add New Memo Field',
    'description': """
        This module customizes the account payment form:
        - Renames the existing 'Memo' field to 'Payment Reference'
        - Adds a new 'Memo' field below the Company Bank Account field
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'views/account_payment_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}