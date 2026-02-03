{
    'name': 'Warehouse Dashboard Filter',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Filter inventory dashboard by warehouse user groups',
    'description': """
        Warehouse-Specific Dashboard Filter
        ====================================
        * Filters inventory overview dashboard to show only relevant warehouse operations
        * Each warehouse user sees only their warehouse's operation types
        * Works with existing warehouse_transfer_automation module
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'stock',
        'warehouse_transfer_automation',  # Depends on your existing module
    ],
    'data': [
        'security/stock_picking_type_security.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}