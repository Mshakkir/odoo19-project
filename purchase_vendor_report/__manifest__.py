{
    'name': 'Purchase Vendor Report',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Purchase Reports by Vendor',
    'description': """
        This module adds a purchase report by vendor feature.
        - Filter by date range and vendors
        - View detailed purchase invoice information
        - Shows vendor, analytic account, purchase account, warehouse, and net amount
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['purchase', 'account', 'stock', 'analytic'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_vendor_report_wizard_view.xml',
        'views/purchase_vendor_report_view.xml',
        'views/purchase_vendor_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}