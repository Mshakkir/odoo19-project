# # -*- coding: utf-8 -*-
# {
#     'name': 'Sales Invoice Reports',
#     'version': '19.0.1.0.0',
#     'category': 'Sales',
#     'summary': 'Sales reports based on customer invoices',
#     'description': """
#         Sales Invoice Reports Module
#         ==============================
#         This module provides comprehensive sales reporting based on customer invoices:
#         * Report by Product
#         * Report by Customer
#         * Report by Salesperson
#
#         All reports are based on invoices (not sale orders) for businesses
#         that create direct invoices.
#     """,
#     'author': 'Your Company',
#     'website': 'https://www.yourcompany.com',
#     'depends': ['account', 'sale_management'],
#     'data': [
#         'security/ir.model.access.csv',
#         'wizard/report_by_product_wizard_view.xml',
#         'wizard/report_by_customer_wizard_view.xml',
#         'wizard/report_by_salesperson_wizard_view.xml',
#         'views/product_report_view.xml',
#         'views/customer_report_view.xml',
#         'views/salesperson_report_view.xml',
#         'views/menu_views.xml',
#     ],
#     'installable': True,
#     'application': False,
#     'auto_install': False,
#     'license': 'LGPL-3',
# }
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
{
    'name': 'Sales Invoice Reports',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Sales reports based on customer invoices',
    'description': """
        Sales Invoice Reports Module
        ==============================
        This module provides comprehensive sales reporting based on customer invoices:
        * Report by Product
        * Report by Customer
        * Report by Salesperson
        * Formatted Sales Report Display
        * Custom PDF Report by Salesperson (Detailed)

        All reports are based on invoices (not sale orders) for businesses 
        that create direct invoices.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['account', 'sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/report_by_product_wizard_view.xml',
        'wizard/report_by_customer_wizard_view.xml',
        'wizard/report_by_salesperson_wizard_view.xml',
        'wizard/sales_report_wizard_view.xml',
        'views/product_report_view.xml',
        'views/customer_report_view.xml',
        'views/salesperson_report_view.xml',
        'views/salesperson_report_display_view.xml',
        'views/menu_views.xml',
        'reports/sales_report_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}