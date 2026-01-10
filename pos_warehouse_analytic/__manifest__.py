{
    'name': 'POS Warehouse Analytic',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Add Warehouse and Analytic Account to POS Sessions',
    'description': """
        This module adds warehouse and analytic account selection to POS sessions.
        - Select warehouse when opening POS session
        - Analytic account auto-populates based on warehouse
        - All transactions in the session are tagged with the analytic account
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'point_of_sale',
        'stock',
        'analytic',
        'purchase'
    ],
    'data': [
        'views/pos_session_views.xml',
        'views/pos_config_views.xml',
    ],
    # Uncomment below if you want to display warehouse info in POS interface
    # 'assets': {
    #     'point_of_sale._assets_pos': [
    #         'pos_warehouse_analytic/static/src/js/controllers.js',
    #     ],
    # },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}