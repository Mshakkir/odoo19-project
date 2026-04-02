# -*- coding: utf-8 -*-
{
    'name': 'Purchase Sales Comparison Report',
    'version': '19.0.1.0.0',
    'summary': 'Purchase and Sales Comparison Report for Inventory',
    'description': """
        This module provides a Purchase vs Sales Comparison Report
        showing Pur.Qty, Pur.Total, Sal.Qty, Sal.Total, Balance Qty
        and Diff.Amount per product for a selected date range.
    """,
    'category': 'Inventory',
    'author': 'Custom',
    'depends': ['stock', 'purchase', 'sale_management', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/purchase_sales_comparison_wizard_view.xml',
        'report/purchase_sales_comparison_report_template.xml',
        'report/purchase_sales_comparison_report.xml',
        'views/inventory_menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
