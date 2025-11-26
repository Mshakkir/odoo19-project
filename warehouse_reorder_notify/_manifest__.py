{
    'name': 'Warehouse Reorder Notification',
    'version': '1.0',
    'author': 'Your Name',
    'depends': ['stock', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/reorder_cron.xml',
    ],
    'installable': True,
}
