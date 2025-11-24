{
    'name': 'Advanced Reorder Notifications',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Automated reorder notifications for all products to warehouse users and admins',
    'description': """
        Advanced Reorder Notification System - Dashboard Only
        ======================================================
        * Monitors all products with reordering rules
        * Sends notifications to user dashboard/inbox (NO EMAIL)
        * Warehouse-specific notifications
        * Detailed product reorder information
        * Daily summary in Odoo Discuss/Activities
        * Beautiful HTML notifications in dashboard
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['stock', 'purchase', 'mail'],
    'data': [
        # 'security/ir.model.access.csv',
        'data/scheduled_actions.xml',
        'views/stock_warehouse_orderpoint_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}