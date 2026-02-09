{
    'name': 'Purchase Buyer Report',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Purchase Reports by Buyer',
    'description': """
        This module adds a purchase report by buyer feature.
        - Filter by date range and buyers
        - View detailed purchase invoice lines with product information
        - Shows date, invoice number, buyer, vendor, warehouse, product, quantity, unit, rate, and net amount
        - Includes optional columns: analytic account, discount, subtotal, tax value
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['purchase', 'account', 'stock', 'analytic'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_buyer_report_wizard_view.xml',
        'views/purchase_buyer_report_view.xml',
        'views/purchase_buyer_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}