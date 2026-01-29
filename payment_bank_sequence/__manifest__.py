{
    'name': 'Bank-Specific Payment Sequences',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Different Payment Sequences for SNB and RAJHI Banks',
    'description': """
        This module creates bank-specific payment sequences:

        Customer Payments:
        - SNB Bank: PREC/SNB/YYYY/XXXXX
        - RAJHI Bank: PREC/RAJHI/YYYY/XXXXX

        Vendor Payments:
        - SNB Bank: PAY/SNB/YYYY/XXXXX
        - RAJHI Bank: PAY/RAJHI/YYYY/XXXXX
    """,
    'author': 'Your Company',
    'depends': ['account'],
    'data': [
        'data/payment_sequence_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}