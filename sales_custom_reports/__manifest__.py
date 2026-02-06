# -*- coding: utf-8 -*-
{
    'name': 'Sales Custom Reports',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Custom Sales Reports by Product, Category, Partner, Warehouse, and Salesman',
    'description': """
        Sales Custom Reports Module
        ============================
        This module adds custom sales report functionality:
        * Report by Product
        * Report by Product Category
        * Report by Partner
        * Report by Warehouse
        * Report by Salesman
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['sale_management', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/sale_report_wizard_views.xml',
        'views/sale_report_views.xml',
        'report/sale_report_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}