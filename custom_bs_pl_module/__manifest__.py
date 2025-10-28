{
    'name': 'Custom Accounting Reports',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Custom Balance Sheet and Profit & Loss Reports',
    'author': 'shakkir',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'account',
        'accounting_pdf_reports',
    ],
    'data': [
        # Security first
        'security/ir.model.access.csv',

        # ✅ Load custom PDF report templates FIRST
        # (so their actions exist before wizards reference them)
        'reports/balance_sheet_pdf.xml',
        'reports/profit_loss_pdf.xml',

        # ✅ Then load wizards (they reference the report actions)
        'wizard/balance_sheet.xml',
        'wizard/profit_loss.xml',

        # Views and menus last
        'views/account_detail_view.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
