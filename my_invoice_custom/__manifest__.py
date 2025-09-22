{
    'name': 'Custom Invoice Report',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Customizations for GCC Invoice Template',
    'description': """
    This module customizes the GCC Arabic/English Invoice template 
    (l10n_gcc_invoice.arabic_english_invoice).
    """,
    'author': 'Your Name',
    'website': 'https://yourcompany.com',
    'depends': [
        'account',
        'l10n_gcc_invoice',
    ],
    'data': [
        'report/report.xml',
        'report/report_templates.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
