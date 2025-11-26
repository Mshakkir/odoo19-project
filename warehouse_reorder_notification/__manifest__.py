{
    'name': 'Warehouse Reordering Notification Dashboard',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Show reordering notifications in dashboard for warehouse users',
    'description': """
        This module displays reordering rule notifications in the dashboard
        for warehouse users and admins based on on-hand quantity.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['stock', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/dashboard_views.xml',
        'views/assets.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'warehouse_reorder_notification/static/src/js/reorder_notification_dashboard.js',
            'warehouse_reorder_notification/static/src/xml/reorder_notification_dashboard.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}