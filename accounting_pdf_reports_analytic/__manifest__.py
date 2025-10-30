{
    'name': 'Accounting PDF Reports - Analytic Filter (extend odoo-mates)',
    'version': '1.0.0',
    'summary': 'Add analytic-account based Profit & Loss printing by extending odoo-mates reports',
    'author': 'You',
    'depends': [
        'account',
        'accounting_pdf_reports',  # odoo mates module name used in your post
        'account_analytic_analysis'  # include analytic module (adjust if your instance uses different)
    ],
    'data': [
        'views/accounting_report_analytic_views.xml',
        'views/action_menu_analytic.xml',
    ],
    'installable': True,
    'application': False,
}
