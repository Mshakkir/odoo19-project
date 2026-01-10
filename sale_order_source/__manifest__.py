{
    'name': 'Sale Order Source',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Add source column to identify eCommerce vs ERP orders',
    'description': """
        This module adds a source field to sale orders to distinguish
        between orders created from eCommerce and ERP.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['sale_management', 'website_sale'],
    'data': [
        'views/templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}