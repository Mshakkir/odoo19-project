# -*- coding: utf-8 -*-
{
    'name': 'Product Profit Margin Report',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Generate Product Profit Margin Reports',
    'description': """
        Product Profit Margin Report
        =============================
        This module provides a comprehensive profit margin analysis report for products.

        Features:
        * Wizard-based report generation
        * Filter by date range, product, group
        * Multiple report types (Short, Detailed, Monthly)
        * Bill mode and form type options
        * Tree view display of profit margins
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'stock', 'sale', 'product'],
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