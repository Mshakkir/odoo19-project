# -*- coding: utf-8 -*-
{
    'name': 'Custom Payment Sequences',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Separate sequences for customer and vendor payments',
    'description': """
        This module customizes payment sequences to:
        - Use PSNB for vendor payments
        - Use PRSNB for customer payments
    """,
    'author': 'Your Company',
    'depends': ['account'],  # Depends on account module
    'data': [
        'data/payment_sequence_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}