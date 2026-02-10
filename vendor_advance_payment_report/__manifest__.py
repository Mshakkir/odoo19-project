# -*- coding: utf-8 -*-
{
    'name': 'Advance Payment Report',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Add Advance Payment Report under Vendors menu',
    'description': """
        This module adds an Advance Payment Report wizard under the Vendors menu in Accounting.
        Features:
        - Date range filter
        - Bank filter
        - Vendor filter
        - Tree view report displaying advance payment details
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/advance_payment_report_wizard_view.xml',
        'views/advance_payment_report_view.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
