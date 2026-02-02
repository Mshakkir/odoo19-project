# -*- coding: utf-8 -*-
{
    'name': 'Invoice Delivery Button',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Add Delivery smart button on Invoices and Credit Notes',
    'description': """
        Invoice Delivery Button
        ========================
        This module adds a 'Delivery' smart button on invoices and credit notes
        that allows users to easily access related deliveries and manually create
        returns using Odoo's standard return process.

        Features:
        ---------
        * Adds a 'Delivery' smart button on invoices and credit notes
        * Shows count of related deliveries
        * Click to view and access the delivery orders
        * Works with direct invoices (when delivery is auto-created)
        * Works with sale order invoices
        * User can manually create returns using Odoo's return button
        * Works seamlessly with Odoo Mates third-party accounting module
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'stock',
    ],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}