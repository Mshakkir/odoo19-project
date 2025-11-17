{
    'name': 'Custom Invoice',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Custom Saudi Invoice Template with ZATCA QR Code',
    'description': """
        Custom Arabic/English invoice with ZATCA QR Code, Stamp, Bank Details,
        Header/Footer customization.
    """,
    'author': 'Your Name',
    'depends': [
        'account',
        'l10n_gcc_invoice',
    ],
    'data': [
        'report/report.xml',
        'report/invoice_template.xml',
        'report/footer_template.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
