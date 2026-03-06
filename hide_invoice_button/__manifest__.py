# -*- coding: utf-8 -*-
{
    'name': 'Hide Invoice View Button in Email',
    'version': '1.0.0',
    'summary': 'Removes the "View Invoice" portal button from invoice email notifications',
    'description': """
        This module overrides the default Odoo invoice email template
        to remove the "View Invoice" button that appears above the custom
        email body when sending invoices to customers.
    """,
    'author': 'Sameer Sharaf Al-Otaibi Trading Company',
    'category': 'Accounting',
    'depends': ['account'],
    'data': [
        'data/mail_template_data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
