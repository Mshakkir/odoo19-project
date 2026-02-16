{
    'name': 'Journal Audit with Details View',
    'version': '1.0.2',
    'depends': ['accounting_pdf_reports'],
    'author': 'Your Name',
    'category': 'Accounting',
    'summary': 'Adds Show Details button to Journal Audit (Odoo 19 Compatible)',
    'description': """
        Extends the Journal Audit report from Odoo Mates accounting_pdf_reports module.

        ✅ Odoo 19 Compatible (uses 'list' view type)

        Features:
        - Show Details button to view filtered journal entries
        - Custom list view with all relevant fields
        - Filters by date range, journals, and target move
        - Group by journal (default)
        - Uses default search capabilities
        - Export to Excel/CSV
    """,
    'data': [
        'views/journal_audit_line_view.xml',
        'wizard/journal_audit_details_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}