{
    'name': 'Custom Payment Receipt',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Custom Payment Receipt with Header and Footer',
    'description': """
        Custom Payment Receipt Report
        ==============================
        - Custom header with company details (English & Arabic)
        - Custom footer with branch details
        - Separate layouts for customer and vendor payments
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['account'],
    'data': [
        'views/report_payment_receipt.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}