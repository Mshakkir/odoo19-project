{
    'name': 'Custom Aged Partner Balance',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Customized Aged Partner Balance Report',
    'description': """
        This module extends the Aged Partner Balance report from Odoo Mates
        with custom features and enhancements.

        Features:
        - Customized aging periods
        - Additional partner information
        - Enhanced filtering options
        - Custom report layout
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'account',
        'accounting_pdf_reports',  # Odoo Mates module
    ],
    'data': [
        'security/ir.model.access.csv',
        'reports/report_aged_partner_custom.xml',
        'wizard/account_aged_trial_balance_custom_view.xml',
        'report/report_definition.xml',
        # 'views/aged_partner_wizard_view.xml',  # Uncomment if you add wizard customization
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}