{
    'name': 'Direct Bill SVL Creator',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Purchase',
    'summary': 'Auto-create SVL for direct vendor bills without PO',
    'description': """
        When posting a vendor bill without a Purchase Order,
        this module automatically creates:
        - Stock Valuation Layers (SVL)
        - Stock Moves
        This ensures Landed Costs show correct Original Values.
    """,
    'author': 'Your Company',
    'depends': [
        'account',
        'stock_account',
        'purchase_stock',
        'stock_landed_costs',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}