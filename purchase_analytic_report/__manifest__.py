{
    'name': 'Purchase Analytic Report',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Purchase Reports by Analytic Account',
    'description': """
        This module adds a purchase report by analytic account feature.
        - Filter by date range and analytic accounts
        - View detailed purchase invoice line information
        - Shows date, invoice number, vendor, warehouse, product details, qty, rate, and net amount
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['purchase', 'account', 'stock', 'analytic'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_analytic_report_wizard_view.xml',
        'views/purchase_analytic_report_view.xml',
        'views/purchase_analytic_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}