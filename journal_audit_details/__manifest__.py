{
    'name': 'Journal Audit with Details View',
    'version': '1.0',
    'depends': ['accounting_pdf_reports'],
    'author': 'Your Name',
    'category': 'Accounting',
    'summary': 'Adds Show Details button to Journal Audit',
    'description': """
        Extends the Journal Audit report from Odoo Mates accounting_pdf_reports module.
        Features:
        - Show Details button to view filtered journal entries
        - Custom tree view with all relevant fields
        - Filters by date range, journals, and target move
    """,
    'data': [
        'views/journal_audit_line_view.xml',
        'wizard/journal_audit_details_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}