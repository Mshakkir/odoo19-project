{
    'name': 'Custom Website Products',
    'version': '19.0.1.0.0',
    'summary': 'Customized products page for website',
    'category': 'Website',
    'author': 'Your Company',
    'depends': ['website', 'website_sale', 'stock', 'sale'],
    'data': [
        'views/product_templates.xml',
        'views/assets.xml',
    ],
    'static': {
        'description': 'Custom CSS and JS files',
    },
    'installable': True,
    'application': False,
}