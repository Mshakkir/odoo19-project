# custom_po_module/__manifest__.py

{
    'name': 'Custom Purchase Order - Partially Billed Column',
    'version': '19.0.1.0',
    'category': 'Purchases',
    'sequence': 10,
    'summary': 'Add Partially Billed column and status to Purchase Orders',
    'description': """
        This module adds:
        1. Partially Billed Amount - Shows the amount billed against a PO
        2. Billed Status - Shows if PO is Not Billed, Partially Billed, or Fully Billed

        Features:
        - Displays partially billed amount in the list view
        - Shows billing status (Not Billed/Partially Billed/Fully Billed)
        - Automatically calculates based on linked invoices
        - Works with both posted and paid invoices
    """,
    'author': 'Your Company',
    'website': 'https://yourcompany.com',
    'depends': [
        'purchase',
        'account',
    ],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}