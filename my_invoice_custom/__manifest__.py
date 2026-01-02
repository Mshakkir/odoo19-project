{
    'name': 'Custom Invoice Report',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Customizations for GCC Invoice Template',
    'description': """
        Custom Arabic/English invoice with ZATCA QR Code, Stamp, and Bank details.
    """,
    'author': 'Your Name',
    'website': 'https://yourcompany.com',
    'depends': [
        'account',
        'l10n_gcc_invoice',  # make sure this exists in Odoo 19
    ],
    'data': [
        'report/report.xml',
        'report/report_templates.xml',
        'report/credit_note_templates.xml',
    ],
    'assets': {},
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
