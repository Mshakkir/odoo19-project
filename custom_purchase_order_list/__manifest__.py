# -*- coding: utf-8 -*-
{
    'name': 'Custom Purchase Order List View (Confirmed Orders)',
    'version': '1.0',
    'category': 'Purchase',
    'summary': 'Customize confirmed purchase order list view with additional fields',
    'description': """
        Customizes the confirmed purchase order list view to display:
        - Order Date
        - Reference (PO Number)
        - Vendor
        - Vendor Reference
        - Warehouse
        - Untaxed Amount
        - Tax Amount
        - Total Amount (Include Tax)
        - Buyer (Purchase Representative)
        - Status
        - Billing Status

        This module is specifically for CONFIRMED Purchase Orders.
        Works together with the Custom Purchase RFQ List View module.
    """,
    'depends': ['purchase', 'purchase_stock'],
    'data': [
        'views/purchase_order_confirmed_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}