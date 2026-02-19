# -*- coding: utf-8 -*-
{
    'name': 'Product Stock Filter Bar',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Add a smart filter bar to Inventory Product list view',
    'description': """
        Adds a persistent filter bar above the product list in Inventory.

        Filters:
        - Product name / internal reference (with autocomplete)
        - Stock status: All / Zero Stock / Negative Stock / In Stock
        - On Hand greater than (number)
        - Product type: Consumable / Storable / Service
        - Sales price range (min → max)

        Keyboard shortcuts:
        - Enter  → Apply filters
        - Escape → Clear filters

        Built with the DOM injection pattern for Odoo 19 CE.
    """,
    'depends': ['stock', 'web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'product_stock_filter/static/src/xml/product_stock_filter.xml',
            'product_stock_filter/static/src/css/product_stock_filter.css',
            'product_stock_filter/static/src/js/product_stock_filter.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
