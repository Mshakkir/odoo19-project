{
    'name': 'Product Stock Ledger',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Stock Ledger showing receive, issue, and balance movements per product',
    'description': """
        Product Stock Ledger
        ====================
        Provides a comprehensive stock ledger list view showing:
        - Product movements (receipts and issues)
        - Balance tracking
        - Warehouse-wise details
        - Invoice status
        - Available under Inventory, Purchase, and Sales menus
    """,
    'author': 'Custom',
    'depends': ['stock', 'purchase', 'sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_stock_ledger_views.xml',
        'views/product_stock_ledger_menus.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
