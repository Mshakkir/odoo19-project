{
    'name': 'Custom Asset Depreciation Post Button',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Assets',
    'summary': 'Add instant Post button to depreciation lines',
    'author': 'Your Company',
    'website': 'https://yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'account_asset',
        'account',
    ],
    'data': [
        'views/asset_depreciation_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
