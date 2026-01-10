{
    'name': 'Delivery Countries Filter',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Filter countries on checkout based on delivery methods',
    'author': 'Your Name',
    'depends': ['sale', 'website_sale', 'delivery'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}