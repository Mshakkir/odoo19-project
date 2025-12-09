# -*- coding: utf-8 -*-
{
    'name': 'Sales Book Reports',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Sales Book, Sales Return & Combined Reports for Saudi Trading',
    'description': """
        Custom Sales Book Reports Module
        ==================================
        * Sales Report
        * Sales Return Report
        * Sales & Sales Return Combined Report
        * Date range filtering
        * Short/Detail view options
        * VAT compliant for Saudi Arabia
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['sale', 'account', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/sales_book_wizard_view.xml',
        'report/sales_book_report.xml',
        'report/sales_book_templates.xml',
        'views/sales_book_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}