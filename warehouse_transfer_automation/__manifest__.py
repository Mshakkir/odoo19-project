{
    'name': 'Flexible Warehouse Transfer Automation',
    'version': '19.0.2.0.0',
    'category': 'Inventory',
    'summary': 'Flexible inter-warehouse transfers with auto-receipt creation',
    'description': """
        Flexible Warehouse Transfer Automation
        =======================================
        * Any warehouse can request from any other warehouse
        * Auto-creates receipt transfer to destination warehouse
        * Auto-updates quantities on validation
        * Sends notifications to relevant warehouse users
        * Warehouse-specific access control
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['stock', 'mail'],
    'data': [
        'security/warehouse_security_groups.xml',
        'security/ir.model.access.csv',
        'security/stock_picking_security.xml',
        'data/mail_template.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}