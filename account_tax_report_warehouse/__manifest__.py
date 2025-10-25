{
    'name': 'Tax Report by Warehouse (Analytic Filter)',
    'version': '1.0',
    'summary': 'Adds analytic/warehouse filter to Tax Report',
    'author': 'Jayaraj KP',
    'depends': ['accounting_pdf_reports'],  # ✅ depends on Odoo Mates module
    'data': [
        'views/account_tax_report_wizard_view.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
