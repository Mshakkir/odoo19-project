{
    'name': 'Custom Accounting Reports',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Custom Balance Sheet and Profit & Loss Reports',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['account', 'accounting_pdf_reports'],
    'data': [
        'security/ir.model.access.csv',
        # 'data/financial_report_data.xml',
        'views/account_detail_view.xml',
        'wizard/balance_sheet.xml',
        'wizard/profit_loss.xml',
        'views/menu.xml',

    ],
    'installable': True,
    'license': 'LGPL-3',
}
