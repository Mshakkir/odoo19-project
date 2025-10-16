{
    "name": "Balance Sheet - Show Details",
    "version": "1.0.0",
    "category": "Accounting",
    "summary": "Add Show Details to Balance Sheet wizard and open account-wise ledger details",
    "author": "shakkir",
    "depends": [
        "account",
        "accounting_pdf_reports"   # odoomates module you referenced
    ],
    "data": [
        "views/accounting_report_inherit_views.xml",
        "views/balance_sheet_line_views.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
