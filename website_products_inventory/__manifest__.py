{
    'name': 'Website Products with Inventory',
    'version': '19.0.1.0.0',
    'category': 'Website',
    'summary': 'Display product inventory details on website',
    'author': 'Your Company',
    'depends': ['website', 'website_sale', 'stock'],
    'data': [
        'views/website_products_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}