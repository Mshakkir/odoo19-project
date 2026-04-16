# -*- coding: utf-8 -*-
{
    'name': 'Landed Cost - Journal Entry Field',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Valuation',
    'summary': 'Shows Journal Entry field on Landed Cost form, like Transfers and Vendor Bill',
    'description': """
Landed Cost - Journal Entry Field
==================================
This module adds a visible "Journal Entry" field to the Landed Cost form view,
displayed alongside the existing Transfers and Vendor Bill fields.

Features:
- Shows the linked Journal Entry directly on the Landed Cost header
- Clickable link to open the full Journal Entry
- Smart button showing count of all related journal entries
- Optional: Link multiple journal entries to a single landed cost
- Landed cost amount can be auto-calculated from linked journal entries
    """,
    'author': 'Custom',
    'depends': [
        'stock_landed_costs',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_landed_cost_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
