# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) PySquad Informetics (<https://www.pysquad.com/>).
#
#    For Module Support : contact@pysquad.com
#
##############################################################################
# -*- coding: utf-8 -*-
{
    'name': 'Purchase Product History',
    'version': '19.0.18.0',
    'category': 'Purchase',
    'summary': 'Product Purchase History',
    'description': """
            This module allows users Keep the record of product purchase history and export in excel.
            """,

    'author': 'Pysquad Informatics LLP',
    'website': 'https://www.pysquad.com',
    'depends': ['base', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/purchase_product_history_wizard_view.xml',
        'views/product_template_view.xml',  # Views should be loaded AFTER wizard
    ],
    'images': [
            'static/description/banner_icon.png'
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}