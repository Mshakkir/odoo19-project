{
    'name': 'Invoice Amount in Words - Arabic',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Add Arabic amount in words for invoices',
    'description': """
        This module extends the invoice functionality to display 
        the total amount in words in both English and Arabic.

        Features:
        - Automatic conversion of invoice amount to Arabic words
        - Support for SAR (Saudi Riyal) currency
        - Compatible with existing invoice templates
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'account',
        'l10n_sa',  # Saudi localization if you're using it
    ],
    'data': [
        # No views needed, just model extension
    ],
    'external_dependencies': {
        'python': ['num2words'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}