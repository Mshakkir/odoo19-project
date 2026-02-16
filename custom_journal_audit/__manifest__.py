# -*- coding: utf-8 -*-
{
    'name': 'Custom Journal Audit',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Customized Journal Audit Report with Manual Journal Selection',
    'description': """
        Custom Journal Audit Module
        ============================
        This module extends the OdooMates accounting_pdf_reports module with:
        - Manual journal selection (no auto-selection)
        - Journal entry number filtering
        - Show Details button functionality
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'accounting_pdf_reports',  # OdooMates module dependency
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/journal_audit_custom_view.xml',
        'report/report_journal_custom.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}