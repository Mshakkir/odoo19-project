{
    'name': 'Trial Balance Detailed Report with Warehouse Filter',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Trial Balance with detailed lines and analytic account filtering',
    'description': """
        Combined module that provides:
        - Detailed trial balance line view
        - Analytic account (warehouse) filtering
        - Journal entry drill-down capability
        - Both PDF and interactive reports
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'account',
        'accounting_pdf_reports',
        'analytic',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/trial_balance_wizard_views.xml',
        'views/trial_balance_line_views.xml',
        # 'views/trial_balance_move_line_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}