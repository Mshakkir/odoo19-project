
# ============================================================================
# PURCHASE REGISTER MODULE FOR ODOO 19 CE
# Complete Custom Module with All Files
# ============================================================================

# ----------------------------------------------------------------------------
# FILE: __manifest__.py
# Location: purchase_register/__manifest__.py
# ----------------------------------------------------------------------------
{
    'name': 'Purchase Register',
    'version': '19.0.1.0.0',
    'category': 'Purchases',
    'summary': 'Comprehensive Purchase Register Report for Tax Compliance',
    'description': """
        Purchase Register Module
        =========================
        * Generate purchase register reports
        * Filter by date range and supplier
        * Export to PDF and Excel
        * Tax-wise breakdown
        * GST/VAT compliance ready
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['purchase', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/purchase_register_wizard_views.xml',
        'reports/purchase_register_report.xml',
        'reports/purchase_register_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}