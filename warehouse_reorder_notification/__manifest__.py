{
    'name': 'Warehouse Reordering Notification Channels',
    'version': '19.0.2.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Warehouse-specific notification channels for reordering rules',
    'description': """
        This module creates dedicated Discuss channels for each warehouse
        and sends reordering rule notifications to warehouse-specific channels.
        Each warehouse gets its own notification channel with relevant users.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['stock', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_warehouse_views.xml',
        'views/menuitem_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}