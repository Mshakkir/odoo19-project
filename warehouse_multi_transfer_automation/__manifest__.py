# -*- coding: utf-8 -*-
{
    'name': 'Multi-Warehouse Transfer Automation',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Multi-directional warehouse transfers with auto-receipts and notifications',
    'description': """
        Multi-Warehouse Transfer Automation
        ====================================
        * Any warehouse can request products from any other warehouse
        * Automatic receipt creation when transfer is validated
        * Real-time notifications to requesting and supplying warehouses
        * Each warehouse validates their part: stock decrease → receipt validation → stock increase
        * Warehouse-specific access control with security groups
        * Support for unlimited warehouses
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['stock', 'mail'],
    'data': [
        'security/warehouse_user_groups.xml',
        'security/ir.model.access.csv',
        'security/warehouse_security_rules.xml',
        'data/mail_templates.xml',
        'views/stock_picking_multi_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}