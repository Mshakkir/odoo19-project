{
    'name': 'Purchase Bypd Report',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Purchase Reports by Products',
    'description': """
        This module adds a purchase report by products feature.
        - Filter by date range and products
        - View detailed purchase invoice lines
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['purchase', 'account'],
    'data': [
        'views/purchase_product_report_wizard_view.xml',
        'views/purchase_product_report_view.xml',
        'views/purchase_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}