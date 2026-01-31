{
    'name': 'Custom Trial Balance Report',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Trial Balance with drill-down',
    'depends': ['account', 'accounting_pdf_reports'],  # if using Odoo Mates
    'data': [
        'views/tb_wizard_views.xml',
        'views/tb_line_views.xml',
        'report/tb_detailed_report.xml',
    ],
    'installable': True,
    'application': False,
}
