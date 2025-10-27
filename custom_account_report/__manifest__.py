{
    'name': 'Custom Tax Report Detail',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Add detailed summary to Odoo Mates Tax Report',
    'depends': ['account', 'accounting_pdf_reports'],
    'data': [
        'views/tax_report_wizard_inherit.xml',
        # 'views/tax_report_detail_line_views.xml',
    ],
    'installable': True,
    'application': False,
}
