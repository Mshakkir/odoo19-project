# -*- coding: utf-8 -*-
{
    'name': 'Warehouse Transfer Automation',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Auto-create receipts and notifications for inter-warehouse transfers',
    'description': """
        Warehouse Transfer Automation
        ==============================
        * Auto-creates second transfer from transit to destination warehouse
        * Sends notification to Main warehouse when branch requests products
        * Sends notification to branch warehouse when Main approves request
        * Warehouse-specific access control with security groups
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['stock', 'mail'],
    'data': [
       'security/warehouse_security_groups.xml',
       'security/ir.model.access.csv',
       'security/stock_picking_security.xml',
       'data/mail_template.xml',
       'views/stock_picking_views.xml',
   ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}