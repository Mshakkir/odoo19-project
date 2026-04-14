# -*- coding: utf-8 -*-
{
    'name': 'Warehouse Analytic Account',
    'version': '19.0.6.0.0',
    'category': 'Inventory/Configuration',
    'summary': 'Auto-apply warehouse analytic account on sales, purchases, invoices and POS',
    'description': """
        Adds an Analytic Account field on each Warehouse.
        Automatically applies to:
        - Sales Quotation & Sales Order
        - Purchase Quotation (RFQ) & Purchase Order
        - Customer Invoice & Credit Note
        - Vendor Bill & Vendor Refund
        - POS Orders & Session Closing Journal Entries (revenue lines only)
        - Stock Moves / Pickings (on validation)
    """,
    'author': 'Custom',
    'depends': [
        'stock',
        'purchase',
        'sale',
        'account',
        'analytic',
        'point_of_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_warehouse_views.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
