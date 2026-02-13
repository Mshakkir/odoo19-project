# {
#     'name': 'Multi Bill Receipt',
#     'version': '19.0.1.0.0',
#     'category': 'Accounting/Accounting',
#     'summary': 'Register receipt against multiple bills at once',
#     'description': """
#         Multi Bill Receipt Module
#         =========================
#         * Register receipt for multiple vendor bills
#         * Select vendor and enter receipt amount
#         * Automatically display unpaid bills
#         * Manually select which bills to pay
#         * Support for partial and full payments
#         * Works without core accounting module
#         * Fixed: Partner ID properly set on journal entry lines for Partner Ledger
#     """,
#     'author': 'Custom Development',
#     'website': 'https://www.example.com',
#     'depends': ['account'],
#     'data': [
#         'security/ir.model.access.csv',
#         'wizard/multi_receipt_wizard_views.xml',
#     ],
#     'installable': True,
#     'application': False,
#     'auto_install': False,
#     'license': 'LGPL-3',
# }
{
    'name': 'Multi Bill Receipt',
    'version': '19.0.1.1.0',
    'category': 'Accounting/Accounting',
    'summary': 'Register receipt against multiple bills at once',
    'description': """
        Multi Bill Receipt Module
        =========================
        * Register receipt for multiple vendor bills
        * Select vendor and enter receipt amount
        * Automatically display unpaid bills
        * Manually select which bills to pay
        * Support for partial and full payments
        * View bill allocation history for each payment
        * Works without core accounting module
        * Fixed: Partner ID properly set on journal entry lines for Partner Ledger
    """,
    'author': 'Custom Development',
    'website': 'https://www.example.com',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/multi_receipt_wizard_views.xml',
        'views/bill_allocation_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}