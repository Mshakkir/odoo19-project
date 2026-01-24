{
    'name': 'Custom Order Lines',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Customize order lines with SN, product code, and reorganized columns',
    'description': """
        This module customizes the order lines to display:
        - Serial Number (SN)
        - Product Code (from product reference)
        - Reorganized columns with discount calculations
        - Hide optional fields (Disc%, Delivery Warehouse, Lead Time, Product Variant)
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
