# -*- coding: utf-8 -*-
{
    'name': 'Product Profit Margin Report',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Generate Product Profit Margin Reports from Sales Invoices',
    'description': """
        Product Profit Margin Report
        =============================
        This module provides a comprehensive profit margin analysis report for products
        based on actual sales invoices.

        Features:
        * Wizard-based report generation
        * Filter by date range, product, category
        * Multiple report types (Short, Detailed, Monthly)
        * Bill mode and form type options
        * Tree view display of profit margins
        * Data sourced from posted customer invoices
        * Profit calculation based on invoice selling price vs product cost
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'stock', 'account', 'product'],  # Added 'account' dependency
    'data': [
        'security/ir.model.access.csv',
        'wizard/product_profit_margin_wizard_view.xml',
        'views/product_profit_margin_report_view.xml',
        'views/menu_items.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}