# -*- coding: utf-8 -*-
{
    'name': 'Payment List Customization',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Fix Amount column using manual exchange rate; dd/mm/yy date format in payment lists',
    'description': """
        Customizes Customer Payments and Vendor Payments list views:
        - Amount column shows value converted using the manually entered exchange rate
          (manual_currency_exchange_rate) instead of the system rate
        - Date column displayed in dd/mm/yy format
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'views/account_payment_list_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
