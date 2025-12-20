{
    'name': 'Custom Product Display',
    'version': '1.0.0',
    'category': 'Website',
    'summary': 'Display product inventory on website shop',
    'description': """
    Custom module to show product inventory details on website products page.
    Displays stock quantities and availability information.
    """,
    'author': 'Your Company',
    'website': 'https://yourwebsite.com',
    'depends': ['website_sale', 'stock'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/templates.xml',
    ],
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