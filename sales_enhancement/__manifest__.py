{
    'name': 'Sales Enhancement - Invoice & Date Filter',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Quick invoice access from Sales & Date range filter',
    'description': """
        1. Direct access to create invoices from Sales menu
        2. Date range filter (From/To) for Sales Orders, Invoices, and Delivery Notes
    """,
    'depends': ['sale_management', 'account', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_menu_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'views/stock_picking_views.xml',
        "views/purchase_menu_views.xml",

    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
