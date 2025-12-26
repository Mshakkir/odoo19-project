# -*- coding: utf-8 -*-
{
    'name': 'Fix Duplicate Followers',
    'version': '1.0.0',
    'category': 'Technical',
    'summary': 'Prevents duplicate follower errors on invoices and other records',
    'description': """
        This module fixes the duplicate key constraint error that occurs
        when trying to add followers that already exist.
        It gracefully handles IntegrityError for mail_followers.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['mail', 'base'],
    'data': [],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}