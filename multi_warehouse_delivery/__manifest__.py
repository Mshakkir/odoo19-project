# {
#     'name': 'Multi-Warehouse Product Delivery',
#     'version': '19.0.1.0.0',
#     'category': 'Sales',
#     'summary': 'Select different warehouses for each product line in sales orders',
#     'description': """
#         This module allows you to:
#         - Select warehouse per product line in sales orders
#         - Automatically create separate deliveries for each warehouse
#         - Track stock from different warehouses in one order
#     """,
#     'author': 'Your Company',
#     'website': 'https://www.yourcompany.com',
#     'depends': ['sale_stock', 'sale_management'],
#     'data': [
#         'views/templates.xml',
#         'views/purchase_order_view.xml',
#         'views/product_stock_view.xml',
#     ],
#     'installable': True,
#     'application': False,
#     'auto_install': False,
#     'license': 'LGPL-3',
# }
{
    'name': 'Multi-Warehouse Product Delivery',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Select different warehouses for each product line in sales orders',
    'description': """
        This module allows you to:
        - Select warehouse per product line in sales orders
        - Automatically create separate deliveries for each warehouse
        - Track stock from different warehouses in one order
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['sale_stock', 'sale_management', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/templates.xml',
        'views/purchase_order_view.xml',


    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
