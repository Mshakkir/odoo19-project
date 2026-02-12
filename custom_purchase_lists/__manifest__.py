# -*- coding: utf-8 -*-
{
    'name': 'Custom Purchase Views (RFQ & Orders)',
    'version': '2.0',
    'category': 'Purchase',
    'summary': 'Unified customization for both RFQ and Purchase Order list views',
    'description': """
        Customizes BOTH the RFQ/Quotation list view AND the Purchase Order list view to display:
        - Order Date / Confirmation Date
        - Reference (PO Number)
        - Vendor
        - Vendor Reference
        - Warehouse
        - AWB/Shipping Reference Number
        - Untaxed Amount
        - Tax Amount
        - Total Amount (Include Tax)
        - Buyer (Purchase Representative)
        - Status
        - Billing Status
        
        Features:
        ========
        - Custom list columns for RFQs/Quotations
        - Custom list columns for confirmed Purchase Orders
        - New field: AWB Number (Shipping Reference)
        - New computed field: Tax Amount
        - New computed field: Receipt Status
        
        This unified module replaces the need for separate custom_purchase_rfq_list 
        and custom_purchase_order_list modules. It handles both views in one module
        to avoid field definition conflicts.
        
        Note: If you have the old modules installed, please uninstall them before
        installing this unified module.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'purchase', 
        'purchase_stock',
    ],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
