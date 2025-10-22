{
    'name': 'Warehouse Financial Reports',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Generate Trial Balance, P&L, Balance Sheet per warehouse',
    'description': 'Attach warehouse to accounting entries and generate warehouse-wise financial reports.',
    'depends': ['account', 'stock'],
    'data': [
        'views/wizard_views.xml',
        'report/trial_balance_report.xml',
    ],
    'installable': True,
    'application': False,
}
