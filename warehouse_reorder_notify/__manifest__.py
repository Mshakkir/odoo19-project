{
    'name': 'Warehouse Reorder Dashboard Notification',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Show notifications when products fall below minimum stock.',
    'depends': ['stock'],
    'data': [
        'views/menu_items.xml',
        'views/reorder_notification_views.xml',
        'data/cron_reorder_check.xml',
    ],
    'installable': True,
    'application': True,
}
