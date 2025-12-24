{
    'name': 'Custom Product Template',
    'version': '1.0',
    'category': 'Website',
    'summary': 'Custom product page template for eCommerce',
    'description': """
        Custom module to inherit and customize the Products page
        Displays products from inventory module
    """,
    'author': 'Your Name',
    'website': 'https://www.yourwebsite.com',
    'depends': [
        'website',
        'website_sale',
        'product',
        'stock',
    ],
    'data': [
        # 'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'custom_product_template/static/src/scss/product_template.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
