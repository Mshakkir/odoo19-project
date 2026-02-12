# -*- coding: utf-8 -*-
{
    'name': 'Custom Purchase Lists (RFQ & Orders)',
    'version': '2.0',
    'category': 'Purchase',
    'summary': 'Customize both RFQ and Purchase Order list views',
    'description': """
        Customizes BOTH the RFQ/Quotation list view AND the Purchase Order list view.
        
        Features:
        - Custom columns for RFQ list
        - Custom columns for confirmed Purchase Order list  
        - New field: AWB Number (Shipping Reference)
        - New computed field: Tax Amount
        - New computed field: Receipt Status
        
        Displays:
        - Order Date / Confirmation Date
        - Reference (PO Number)
        - Vendor
        - Vendor Reference
        - Warehouse
        - AWB/Shipping Reference
        - Untaxed Amount
        - Tax Amount (NEW)
        - Total Amount
        - Buyer
        - Status
        - Billing Status
    """,
    'depends': [
        'purchase', 
        'purchase_stock',
    ],
    'data': [
        'views/purchase_order_views.xml',
        'views/purchase_order_confirmed_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
