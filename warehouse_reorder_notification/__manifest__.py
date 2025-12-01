{
    'name': 'Warehouse Reordering System Notifications',
    'version': '19.0.3.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Show reorder notifications in Odoo notification center (bell icon)',
    'description': """
        This module sends reordering rule notifications to Odoo's notification center.
        Warehouse users receive notifications in the bell/clock icon at the top.
        Notifications are warehouse-specific and show directly in the system.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['stock', 'mail', 'purchase'],
    'data': [
        'data/mail_activity_type_data.xml',
        'security/stock_warehouse_orderpoint_security.xml',
        'security/ir.model.access.csv',
        'views/stock_warehouse_orderpoint_views.xml',
        'views/stock_warehouse_orderpoint_actions.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
