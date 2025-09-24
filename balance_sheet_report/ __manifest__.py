{
    'name': 'Balance Sheet Report',
    'version': '1.0',
    'summary': 'Custom Balance Sheet Report',
    'sequence': 10,
    'depends': ['account'],
    'data': [
        'report/balance_sheet_report.xml',
        'report/balance_sheet_template.xml',
    ],
    'installable': True,
    'application': False,
}
