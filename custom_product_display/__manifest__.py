{
    'name': 'Custom Product Display',
    'version': '19.0.1.0.0',
    'category': 'Website',
    'summary': 'Display product details from inventory on website',
    'description': """
        Custom module to override products page and display product details from inventory.
        Shows available stock quantities and locations for products.
    """,
    'author': 'Your Company',
    'website': 'https://yourwebsite.com',
    'depends': ['website', 'website_sale', 'stock'],
    'data': [
        'views/templates.xml',
        'views/assets.xml',
    ],
    'demo': [],
    'assets': {
        'web.assets_frontend': [
            'custom_product_display/static/src/css/custom_product.css',
            'custom_product_display/static/src/js/website_product.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}