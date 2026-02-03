# -*- coding: utf-8 -*-
{
    'name': 'Warehouse Dashboard Filter',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Filter Inventory Overview by User Warehouse',
    'description': """
        This module filters the Inventory Overview dashboard to show only
        operations related to warehouses assigned to the current user.

        Features:
        - Assign multiple warehouses to users
        - Filter dashboard cards by warehouse
        - Show only relevant operations (Receipts, Deliveries, Internal Transfers)
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}