# -*- coding: utf-8 -*-
{
    'name': 'Warehouse Dashboard Operation Filter',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Filter dashboard operation cards by warehouse while allowing inter-warehouse transfers',
    'description': """
Warehouse Dashboard Operation Filter
=====================================
* Hides other warehouses' operation type cards from dashboard
* Each warehouse user sees ONLY their warehouse's operation cards
* Still allows validating inter-warehouse transfers (no access errors)
* Works by overriding search_read() method to filter dashboard queries
* Direct record access (browse/read) remains unrestricted for transfers
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'stock',
        'warehouse_transfer_automation',
    ],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}