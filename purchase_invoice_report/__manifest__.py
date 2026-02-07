{
    'name': 'Purchase Invoice Report',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Purchase Reports by Invoice Number',
    'description': """
        This module adds a purchase report by invoice number feature.
        - Filter by date range and invoice numbers
        - View detailed purchase invoice lines with product information
        - Shows date, invoice number, vendor, warehouse, product, quantity, unit, rate, and net amount
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['purchase', 'account', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_invoice_report_wizard_view.xml',
        'views/purchase_invoice_report_view.xml',
        'views/purchase_invoice_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}