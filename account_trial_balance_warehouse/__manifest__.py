# {
#     'name': 'Trial Balance - Warehouse Filter',
#     'version': '19.0.1.0.0',
#     'category': 'Accounting/Accounting',
#     'summary': 'Filter Trial Balance by Analytic Accounts (Warehouses)',
#     'description': """
#         Adds analytic account filtering to Trial Balance Report
#         =========================================================
#
#         Features:
#         ---------
#         * Filter trial balance by warehouse (analytic accounts)
#         * Support for multiple warehouse selection
#         * Proportional balance calculation for split transactions
#         * Compatible with OdooMates accounting_pdf_reports module
#
#         Usage:
#         ------
#         1. Go to Accounting > Reporting > Trial Balance
#         2. Select date range and display options
#         3. Select warehouse(s) in "Analytic Accounts (Warehouses)" field
#         4. Generate report
#
#         Leave warehouse field empty for combined report (all warehouses).
#     """,
#     'author': 'Your Company',
#     'website': 'https://www.yourcompany.com',
#     'license': 'LGPL-3',
#     'depends': [
#         'account',
#         'analytic',
#         'accounting_pdf_reports',  # OdooMates module
#     ],
#     'data': [
#         'views/account_trial_balance_wizard_view.xml',
#     ],
#     'installable': True,
#     'application': False,
#     'auto_install': False,
# }

{
    'name': 'Trial Balance - Warehouse Filter',
    'version': '19.0.1.0.1',
    'category': 'Accounting/Accounting',
    'summary': 'Filter Trial Balance by Analytic Accounts (Warehouses)',
    'description': """
        Adds analytic account filtering to Trial Balance Report
        =========================================================

        Features:
        ---------
        * Filter trial balance by warehouse (analytic accounts)
        * Support for multiple warehouse selection
        * Proportional balance calculation for split transactions
        * Compatible with OdooMates accounting_pdf_reports module

        Usage:
        ------
        1. Go to Accounting > Reporting > Trial Balance
        2. Select date range and display options
        3. Select warehouse(s) in "Analytic Accounts (Warehouses)" field
        4. Generate report

        Leave warehouse field empty for combined report (all warehouses).

        Version 19.0.1.0.1:
        -------------------
        * Fixed issue where PDF report showed empty when no analytic filter selected
        * Improved handling of empty analytic account lists
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'analytic',
        'accounting_pdf_reports',  # OdooMates module
    ],
    'data': [
        'views/account_trial_balance_wizard_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}