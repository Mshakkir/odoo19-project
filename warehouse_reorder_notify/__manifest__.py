{
    'name': 'Warehouse Reorder Dashboard Notification',
    'version': '1.0.0',
    'category': 'Inventory/Stock',
    'summary': 'Displays notifications when products fall below minimum stock levels.',
    'description': """
Warehouse Reorder Dashboard Notification
========================================
This module checks product stock levels and notifies users when quantities fall
below the minimum defined threshold. Includes:
- Reorder Alerts Dashboard
- Cron job to check stock levels
- Menu Item for Notification List
    """,

    'author': 'Your Company Name',
    'website': 'https://www.yourwebsite.com',

    # 🔐 Recommended for all Odoo custom modules
    'license': 'LGPL-3',

    'depends': [
        'stock',
    ],

    'data': [
        # 'views/menu_items.xml',
        'views/reorder_notification_views.xml',
        'data/cron_reorder_check.xml',
    ],

    'installable': True,
    'application': True,
}
