{
"name": "Custom BS_P&l",
"version": "1.0.0",
"summary": "Add warehouse analytic account filter + combined totals to accounting reports (Balance Sheet / P&L) without editing upstream files.",
"category": "Accounting/Reporting",
"author": "Your Name",
"website": "",
"license": "AGPL-3",
"depends": [
"account",
"accounting_pdf_reports"
],
"data": [
"views/accounting_report_view_inherit.xml",
"security/ir.model.access.csv"
],
"installable": True,
"application": False,
}