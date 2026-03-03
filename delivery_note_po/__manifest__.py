{
    'name': 'Stock Picking Customer Reference',
    'version': '1.0',
    'summary': 'Show Sale Order Customer Reference in Delivery Order',
    'depends': ['stock', 'sale_management'],
    'data': [
        'views/stock_picking_view.xml',
    ],
    'installable': True,
    'application': False,
}