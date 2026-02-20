{
    'name': 'Delivery Note - Delivery Address',
    'version': '19.0.1.0.0',
    'summary': 'Adds Delivery Address field to Delivery Notes',
    'author': 'Custom',
    'category': 'Inventory',
    'depends': ['stock'],
    'data': [
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}