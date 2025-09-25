# -*- coding: utf-8 -*-
# Part of Waleed Mohsen. See LICENSE file for full copyright and licensing details.

{
    'name': 'Restore Create Bill Button (Odoo 19)',
    'version': '1.0.0',
    'category': 'Purchase',
    'summary': "Bring back the Create Bill button in Purchase Orders alongside Upload Bill (Odoo 19).",
    'description': """
Restore Create Bill Button in Purchase Orders (Odoo 19)
=======================================================

In Odoo 19, the familiar **Create Bill** button in Purchase Orders was replaced with **Upload Bill**, 
which caused difficulties for users relying on quick bill creation.  

This module restores the **Create Bill** button while keeping Odoo’s **Upload Bill**, 
giving you both workflows in one view.

Key Features:
-------------
- Restore the **Create Bill** button in Purchase Orders.  
- Keep the new **Upload Bill** option from Odoo 19.  
- Maintain both classic and modern bill workflows.  
- Fully compatible with Odoo 19 Community & Enterprise.  

   Keywords: Odoo 19, Purchase, Create Bill, Upload Bill, Vendor Bill, Purchase Order, Bill Creation, Vendor Invoice
    """,
    'license': 'OPL-1',
    'author': 'Waleed Mohsen',
    'support': 'mohsen.waleed@gmail.com',
    'depends': ['purchase'],
    'data': [
        "views/purchase_order_view.xml",
    ],
    'images': ['static/description/main_screenshot.png'],
    'installable': True,
    'auto_install': False,
}
