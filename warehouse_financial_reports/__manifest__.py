
# ============================================
# MODULE: warehouse_financial_reports
# ============================================
# This module extends Odoo Mates accounting_pdf_reports
# to generate separate financial reports per warehouse
# ============================================

# ==========================================
# __manifest__.py
# ==========================================
{
    'name': 'Warehouse-wise Financial Reports',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Generate separate financial reports for each warehouse/branch',
    'description': """
        Extends Odoo Mates accounting reports to generate:
        - Individual Trial Balance per warehouse
        - Individual Balance Sheet per warehouse  
        - Individual Profit & Loss per warehouse
        - Consolidated reports (all warehouses combined)
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['accounting_pdf_reports', 'analytic', 'stock'],
    'data': [

        'wizard/warehouse_trial_balance_view.xml',
        'reports/warehouse_trial_balance_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
