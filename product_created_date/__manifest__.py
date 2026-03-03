{
    'name': 'Product Created Date',
    'version': '19.0.1.0.0',
    'summary': 'Adds auto-filled Created Date field to Product form',
    'description': """
        This module adds a 'Created Date' field (dd/mm/yy format) to the 
        product template form view. The date is automatically set when 
        a product is created and is read-only.
    """,
    'author': 'Custom',
    'category': 'Inventory',
    'depends': ['product'],
    'data': [
        'views/product_template_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
