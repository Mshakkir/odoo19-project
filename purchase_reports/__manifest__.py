# -*- coding: utf-8 -*-
{
    'name': 'Purchase Reports',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Comprehensive Purchase Reports with Filters',
    'description': """
        Purchase Reports Module
        =======================
        * Multiple purchase report types
        * Filter wizard before viewing reports
        * PDF and Excel export options
        * Various grouping options
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['purchase', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'report/purchase_report.xml',
        'report/purchase_report_templates.xml',
        'views/purchase_report_views.xml',
        'views/purchase_report_menus.xml',
        'wizard/purchase_report_by_vouchers_wizard.xml',
        'wizard/purchase_report_by_product_wizard.xml',
        'wizard/purchase_report_by_category_wizard.xml',
        'wizard/purchase_report_by_product_group_wizard.xml',
        'wizard/purchase_report_by_party_wizard.xml',
        'wizard/purchase_report_by_party_group_wizard.xml',
        'wizard/purchase_report_by_warehouse_wizard.xml',
        'wizard/purchase_report_by_salesman_wizard.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}