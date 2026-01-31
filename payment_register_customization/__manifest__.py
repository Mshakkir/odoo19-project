# -*- coding: utf-8 -*-
{
    'name': 'Payment Register Customization',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Customize Payment Register Form - Add Memo Field',
    'description': """
        This module customizes the payment register wizard:
        - Renames 'Memo' field to 'Reference Number'
        - Adds a new 'Memo' field
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['account'],
    'data': [
        'views/account_payment_register_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}