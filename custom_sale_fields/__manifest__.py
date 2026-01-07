{
    'name': 'Custom Sale Order Fields',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Add Customer Reference and AWB fields to Sale Order form',
    'description': """
        This module adds Customer Reference and AWB fields 
        below Payment Terms in Sale Order and Quotation forms.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['sale_management'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}