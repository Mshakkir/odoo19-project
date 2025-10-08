{
    'name': 'Purchase Product History',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Show purchase, stock, and sale history in RFQ product lines',
    'description': """
        Purchase Product History
        ========================
        This module adds product history information to RFQ lines:
        - Purchase history with last price and average price
        - Stock movement history
        - Sale order history
        - Quick access buttons to view detailed history
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['purchase', 'stock', 'sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}