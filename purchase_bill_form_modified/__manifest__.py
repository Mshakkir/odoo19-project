{
    'name': 'Modified Vendor Bill form with PO, GR, AWB',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Add PO, Goods Receipt, and AWB fields to vendor bills',
    'author': 'Your Name',
    'depends': ['account', 'purchase', 'stock','purchase_order_awb'],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
}