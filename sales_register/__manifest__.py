

{
    'name': 'Sales Register',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Comprehensive Sales Register Report for Tax Compliance',
    'description': """
        Sales Register Module
        =========================
        * Generate sales register reports
        * Filter by date range and customer
        * Export to PDF and Excel
        * Tax-wise breakdown
        * GST/VAT compliance ready
        * Summary and Detailed reports
        * Date filters: Daily, Weekly, Monthly, Yearly, Custom
        * Show Details in Tree View
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['sale', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/sales_register_wizard_views.xml',
        'wizard/sales_register_details_views.xml',
        'reports/sales_register_report.xml',
        'reports/sales_register_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}