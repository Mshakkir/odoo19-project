# -*- coding: utf-8 -*-
{
    'name': 'Hide Invoice View Button in Email',
    'version': '2.0.0',
    'summary': 'Removes "View Invoice" button and fixes auto To field in invoice emails',
    'description': """
        Fix 1: Removes the "View Invoice" button injected by Odoo above the invoice email body.
        Fix 2: Restores auto-fill of customer email in the "To" field when sending invoices.
    """,
    'author': 'Sameer Sharaf Al-Otaibi Trading Company',
    'category': 'Accounting',
    'depends': ['account', 'mail'],
    'data': [
        'data/mail_template_data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
