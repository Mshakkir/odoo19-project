{
    'name': 'Warehouse Transfer Request System',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Inter-warehouse transfer requests with notifications and virtual transit',
    'description': """
        Warehouse Transfer Request System
        ==================================
        * Users can request products from other warehouses
        * Email notifications for request approval
        * Auto-create delivery and receipt operations
        * Virtual transit location support
        * Automatic stock quantity updates
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['stock', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template.xml',
        'views/warehouse_transfer_request_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}