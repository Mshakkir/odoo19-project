# -*- coding: utf-8 -*-
{
    'name': 'Purchase Bill Update Product Cost',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Updates product cost price automatically when a vendor bill is posted',
    'description': """
        When a vendor bill (supplier invoice) is confirmed/posted,
        this module automatically updates the product's cost price
        (Standard Price) with the unit price from the bill line.

        Features:
        - Updates cost only on bill confirmation (post)
        - Respects product costing method (Standard Price / AVCO / FIFO)
        - Logs a chatter message on the product for traceability
        - Skips products with no valid unit price
        - Works with multi-currency (converts to company currency)
    """,
    'author': 'Custom Development',
    'depends': ['account', 'purchase', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
