{
    'name': 'Custom Tax Report Detail',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Add detailed summary to Odoo Mates Tax Report',
    'depends': ['account'],
    'data': [
        'views/tax_report_detail_views.xml',
        'views/tax_report_wizard_inherit.xml'
    ],
    'installable': True,
    'application': False,
}
