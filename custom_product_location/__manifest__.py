{
    'name': 'Product Default Location',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Set default location/rack for products',
    'depends': ['stock', 'sale_stock', 'purchase_stock'],
    'data': [
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
}