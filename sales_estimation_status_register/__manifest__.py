{
    'name': 'Sales Estimation Status Register',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Sales Estimation Status Register Report',
    'description': """
        Sales Estimation Status Register
        ==================================
        * Generate Sales Estimation Status Reports
        * Filter by Type, Form Type, Bill Mode, Party
        * Filter by Confirmed / Cancelled Status
        * Date filters: Daily, Weekly, Monthly, Quarterly, Yearly, Custom
        * Show Details in Tree View
        * Export to PDF and Excel
        * Ledger Currency Support
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['sale'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/sales_estimation_status_wizard_views.xml',
        'wizard/sales_estimation_status_details_views.xml',
        'reports/sales_estimation_status_report.xml',
        'reports/sales_estimation_status_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}