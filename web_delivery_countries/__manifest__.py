{
    'name': 'Website Delivery Countries Filter',
    'version': '19.0.1.0.0',
    'category': 'Website/eCommerce',
    'summary': 'Filter checkout countries based on active delivery methods',
    'author': 'Your Name',
    'depends': ['website_sale', 'delivery'],
    'data': [
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'web_delivery_countries/static/src/js/checkout_country_filter.js',
        ],
    },
    'installable': True,
    'auto_install': False,
}