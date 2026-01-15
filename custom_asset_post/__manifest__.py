{
    'name': 'Asset Depreciation Post Button',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Assets',
    'summary': 'Add Post button to depreciation line wizard',
    'author': 'Your Company',
    'website': 'https://yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'om_account_asset',
    ],
    'data': [
        'views/asset_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}