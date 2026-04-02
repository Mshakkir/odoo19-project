# -*- coding: utf-8 -*-
{
    'name': 'Purchase Sales Comparison Report',
    'version': '19.0.2.0.0',
    'summary': 'Purchase and Sales Comparison Report for Inventory',
    'description': """
        Purchase vs Sales Comparison Report showing Pur.Qty, Pur.Total,
        Sal.Qty, Sal.Total, Balance Qty and Diff.Amount per product
        for a selected date range. Opens as an interactive window.
    """,
    'category': 'Inventory',
    'author': 'Custom',
    'depends': ['stock', 'purchase', 'sale_management', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/purchase_sales_comparison_wizard_view.xml',
        'views/inventory_menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
