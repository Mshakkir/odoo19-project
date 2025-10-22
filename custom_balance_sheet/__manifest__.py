{
    "name": "Custom Balance Sheet",
    "version": "19.0.1.0.0",
    "summary": "Custom balance sheet with wizard, PDF, and detailed view",
    "category": "Accounting",
    "author": "You",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "views/menus_actions.xml",
        "views/wizard_views.xml",
        "views/balance_sheet_line_views.xml",
        "reports/balance_sheet_template.xml",
        "reports/balance_sheet_report_action.xml",
    ],
    "installable": True,
    "auto_install": False,
}
