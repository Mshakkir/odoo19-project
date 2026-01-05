{
    'name': 'Dynamic Product Categories',
    'version': '1.0',
    'category': 'Website',
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
        'product',
        'website',
    ],
    'data': [
        'views/category_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            # Add any additional CSS/JS files here if needed
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}