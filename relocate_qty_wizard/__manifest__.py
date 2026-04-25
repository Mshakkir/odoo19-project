# -*- coding: utf-8 -*-
{
    'name': 'Relocate Stock Quant - Quantity Adjustment',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Adds an editable product/quantity table to the existing Relocate wizard.',
    'author': 'Custom',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/relocate_qty_line_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
