{
    'name': 'Purchase Product Category Report',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Purchase Reports by Product Category',
    'description': """
        This module adds a purchase report by product category feature.
        - Filter by date range and product categories
        - View detailed purchase invoice lines with product information
        - Shows date, invoice number, vendor, warehouse, buyer, product category, product, quantity, unit, rate, discount, untaxed amount, tax value, and net amount
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['purchase', 'account', 'stock', 'analytic'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_product_category_report_wizard_view.xml',
        'views/purchase_product_category_report_view.xml',
        'views/purchase_product_category_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
