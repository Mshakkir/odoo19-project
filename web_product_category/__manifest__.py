{
    'name': 'Dynamic Product Categories',
    'version': '1.0.0',
    'category': 'Product',
    'summary': 'Dynamic product category showcase',
    'description': """
        Display product categories dynamically from Odoo database
        Features:
        - Dynamic category loading
        - Category images
        - Product count
        - Responsive design
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'web',
        'product',
    ],
    'data': [
        'views/category_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}