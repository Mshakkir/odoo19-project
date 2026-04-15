{
    'name': 'Custom Partner Ledger Report',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Customized Partner Ledger Report with Manual Exchange Rate',
    'description': """
        Extends the Odoo Mates Partner Ledger Report with:
        - Manual exchange-rate field in the wizard (1 INR = X SAR display)
        - Exchange rate applied per-line in the PDF report
        - Exchange rate shown in the Show Details list view
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'accounting_pdf_reports',
    ],
    'data': [
        # 'security/ir_model_access.csv',
        'reports/report_partner_ledger_template.xml',
        'views/partner_ledger_wizard_view.xml',
        'views/partner_ledger_detail_view.xml',
        'views/partner_ledger_menu_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}