{
    'name': 'Sale Analytic Warehouse Auto-Selection',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Auto-select warehouse based on analytic account in sale order lines',
    'description': """
        This module automatically selects the warehouse in sale order lines
        based on the analytic account chosen in analytic distribution.
        Warehouses must have the same name as analytic accounts.
    """,
    'author': 'Your Name',
    'depends': ['sale_stock', 'analytic','purchase_stock'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}