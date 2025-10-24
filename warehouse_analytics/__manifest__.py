# -*- coding: utf-8 -*-
{
    'name': 'Warehouse Analytics for Trial Balance',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Complete warehouse-based financial reporting with all accounts',
    'description': """
        This module ensures ALL accounts (including receivables, payables, bank accounts)
        appear in warehouse-specific trial balance reports.

        Features:
        - Warehouse/Branch field on invoices and bills
        - Automatic analytic propagation to all journal entries
        - Integration with sales orders and purchase orders
        - Complete trial balance by warehouse
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'account',
        'stock',
        'sale_management',
        'purchase',
        'analytic',
        'accounting_pdf_reports',
    ],
    'data': [
        'views/account_move_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
