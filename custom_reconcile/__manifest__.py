# -*- coding: utf-8 -*-
{
    'name': 'Custom Reconciliation',
    'version': '19.0.1.0.0',
    'summary': 'Enhanced Bank & Partner Reconciliation for Odoo 19 CE',
    'description': """
        Custom Reconciliation Module for Odoo 19 Community Edition.
        Features:
        - Bank Statement Reconciliation Interface
        - Partner Reconciliation (Receivables/Payables)
        - Reconciliation Rules/Models
        - Write-off Support
        - Partial Payment Matching
        - Multi-line Reconciliation Wizard
        - Reconciliation Dashboard
    """,
    'category': 'Accounting/Accounting',
    'author': 'Your Company',
    'website': 'https://yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'base',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_reconcile_model_views.xml',
        'views/account_bank_statement_views.xml',
        'views/account_reconcile_wizard_views.xml',
        'views/account_partner_reconcile_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_reconcile/static/src/css/reconcile.css',
            'custom_reconcile/static/src/js/reconcile_widget.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}