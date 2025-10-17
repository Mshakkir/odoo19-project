{
    "name": "Custom Balance Sheet",
    "version": "1.0",
    "summary": "Custom Balance Sheet Report for Odoo 19 CE",
    "category": "Accounting",
    "author": "Muhammed Shakkir T",
    "depends": [
        "base",
        "web",
        "account"
    ],
    "data": [
        "views/balance_sheet_menu.xml",
        "wizard/balance_sheet_wizard_view.xml",
        "report/balance_sheet_template.xml",
        "report/report_action.xml",
    ],
    "installable": True,
    "application": True,
}
