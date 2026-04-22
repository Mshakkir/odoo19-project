# -*- coding: utf-8 -*-
{
    'name': 'Product Purchase & Sale Report',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Combined Purchase Bill & Sales Invoice Report per Product with Unit Rates',
    'description': """
        This module adds a combined Purchase & Sales report per product
        accessible from the Inventory > Products menu.
        
        Features:
        - View Bill Number (Vendor Bill) per product
        - View Receipt Number (Purchase Receipt/Delivery) per product
        - View Sales Invoice Number per product
        - View Sales Delivery per product
        - Unit Rate for both purchase and sale
        - Filter by date, product, vendor, customer
        - Opens in a new window as a list/pivot view
    """,
    'author': 'Custom Development',
    'depends': [
        'stock',
        'purchase',
        'sale',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_purchase_sale_report_views.xml',
        'views/product_purchase_sale_report_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
