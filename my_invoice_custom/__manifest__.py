{
    'name': 'Custom Invoice Report',
    'version': '16.0.1.0.0',   # OCA style or just "1.0" works too
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
    ],
    'assets': {
        'web.report_assets_common': [
            'my_invoice_custom/static/src/css/custom_report.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
