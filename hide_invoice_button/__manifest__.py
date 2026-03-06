# -*- coding: utf-8 -*-
{
    'name': 'Hide Invoice View Button in Email',
    'version': '3.0.0',
    'summary': 'Removes "View Invoice" button and fixes auto To field in invoice emails',
    'description': """
        Fix 1: Removes the "View Invoice" portal button from invoice email notifications.
                Source: account_move.py _notify_get_action_link (line ~5992)
        Fix 2: Auto-fills customer email in the "To" field when sending invoices.
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
