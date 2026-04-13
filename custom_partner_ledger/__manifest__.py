# -*- coding: utf-8 -*-
{
    'name': 'Custom Partner Ledger Report',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Customized Partner Ledger Report',
    'description': """
        This module extends the Odoo Mates Partner Ledger Report
        with custom modifications and enhancements.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'accounting_pdf_reports',  # Odoo Mates module
    ],
    'data': [
        'reports/report_partner_ledger_template.xml',
        'views/partner_ledger_wizard_view.xml',
        'views/partner_ledger_detail_view.xml',
        'views/partner_ledger_menu_view.xml',


    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}