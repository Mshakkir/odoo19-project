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
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/balance_sheet.xml',
        'wizard/profit_loss.xml',
        'views/account_detail_view.xml',
        'views/menu.xml',
        'views/report_financial_custom.xml',

    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
