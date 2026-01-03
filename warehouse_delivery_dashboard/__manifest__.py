{
    'name': 'Warehouse Delivery Dashboard',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Dashboard for warehouse-specific delivery orders - No JS',
    'description': """
        This module adds a dashboard to display pending delivery orders
        for warehouse users using pure Python and XML views.
        No JavaScript required - uses standard Odoo components.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['stock', 'sale_stock', 'board'],
    'data': [
        'security/ir.model.access.csv',
        'views/delivery_dashboard_views.xml',
        'views/stock_picking_views.xml',
        'views/res_users_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}