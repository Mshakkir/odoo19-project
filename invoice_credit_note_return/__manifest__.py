# -*- coding: utf-8 -*-
{
    'name': 'Invoice Credit Note Return',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Add Return button on Credit Notes to process stock returns',
    'description': """
        Invoice Credit Note Return
        ===========================
        This module adds a 'Return' button on credit note invoices that allows
        users to easily process stock returns after creating a credit note.

        Features:
        ---------
        * Adds a 'Return' button at the top of credit note forms
        * Creates reverse stock transfers for returned products
        * Links returns with their corresponding credit notes
        * Works with Odoo Mates third-party accounting module
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'stock',
        'sale_stock',
    ],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}