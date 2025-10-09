{
    'name': 'Purchase RFQ Product History Tabs',
    'version': '19.0.1.0.0',
    'category': 'Purchases',
    'summary': 'Add Stock, Sales, and Purchase history tabs in RFQ form',
    'depends': ['purchase', 'stock', 'sale_management'],
    'data': [
        'views/purchase_order_view.xml',
    ],
    'installable': True,
    'application': False,
}
