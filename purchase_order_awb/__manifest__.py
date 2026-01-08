{
    'name': 'Purchase Order AWB Number',
    'version': '1.0',
    'category': 'Purchases',
    'summary': 'Add AWB Number field to Purchase Orders',
    'author': 'Your Name',
    'depends': ['purchase', 'stock'],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
}