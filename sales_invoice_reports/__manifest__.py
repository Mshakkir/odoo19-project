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
        * Report by Analytic Account
        * Report by Invoice Number
        * Report by Product Category
        * Formatted Sales Report Display
        * Custom PDF Report by Salesperson (Detailed)

        All reports are based on invoices (not sale orders) for businesses 
        that create direct invoices.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['account', 'sale_management', 'analytic'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/report_by_product_wizard_view.xml',
        'wizard/report_by_customer_wizard_view.xml',
        'wizard/report_by_salesperson_wizard_view.xml',
        'wizard/report_by_analytic_account_wizard_view.xml',
        'wizard/report_by_invoice_number_wizard_view.xml',
        'wizard/report_by_product_category_wizard_view.xml',
        'wizard/sales_report_wizard_view.xml',
        'views/product_report_view.xml',
        'views/customer_report_view.xml',
        'views/salesperson_report_view.xml',
        'views/analytic_account_report_view.xml',
        'views/invoice_number_report_view.xml',
        'views/product_category_report_view.xml',
        'views/menu_views.xml',
        'reports/sales_report_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}