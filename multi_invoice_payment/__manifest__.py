{
    'name': 'Multi Invoice Payment',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Register payment against multiple invoices at once',
    'description': """
        Multi Invoice Payment Module
        =============================
        * Register payment for multiple customer invoices
        * Select customer and enter payment amount
        * Automatically display unpaid invoices
        * Manually select which invoices to pay
        * Support for partial and full payments
        * Works without core accounting module
    """,
    'author': 'Custom Development',
    'website': 'https://www.example.com',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/multi_payment_views.xml',
        'wizard/multi_payment_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}