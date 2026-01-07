{
    'name': 'Dynamic Product Category Page',
    'version': '19.0.1.0.0',
    'category': 'Website',
    'summary': 'Dynamic product category showcase on website',
    'description': """
        This module extends the website category page to dynamically display
        product categories from Odoo inventory with images and descriptions.
    """,
    'author': 'Your Company',
    'depends': ['website', 'product', 'website_sale'],
    'data': [
        'views/website_category_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}