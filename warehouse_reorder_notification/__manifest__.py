{
    'name': 'Warehouse Reordering Notification in Discuss',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Show reordering notifications in Discuss for warehouse users',
    'description': """
        This module sends reordering rule notifications to Discuss app
        for warehouse users and admins based on on-hand quantity.
        Notifications appear as messages from ReorderBot in Discuss.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['stock', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/reorder_bot_data.xml',
        'views/menuitem_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}