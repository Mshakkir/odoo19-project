# -*- coding: utf-8 -*-
{
    'name': 'Asset Depreciation Post Button',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Add Post button to depreciation lines',
    'description': """
        Extends om_account_asset module to add:
        - Post button on depreciation lines
        - Easy posting of depreciation entries
    """,
    'author': 'Your Name',
    'website': 'https://yourwebsite.com',
    'depends': [
        'om_account_asset',  # OdooMates Asset module
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_asset_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}