# -*- coding: utf-8 -*-
{
    'name': 'Custom Purchase RFQ List View',
    'version': '1.0',
    'category': 'Purchase',
    'summary': 'Customize purchase order/quotation list view with additional fields',
    'description': """
        Customizes the purchase order (RFQ/quotation) list view to display:
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
    """,
    'depends': ['purchase', 'purchase_stock'],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}