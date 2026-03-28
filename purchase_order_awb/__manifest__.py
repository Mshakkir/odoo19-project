{
    'name': 'Purchase Order AWB Number',
    'version': '1.0',
    'category': 'Purchases',
    'summary': 'Add AWB Number field to Purchase Orders',
    'author': 'Your Name',
    'depends': ['purchase', 'stock', 'account'],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'purchase_order_awb/static/src/js/hide_po_currency_total.js',
        ],
    },
    'installable': True,
    'application': False,
}

