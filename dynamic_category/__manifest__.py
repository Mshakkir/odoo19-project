# -*- coding: utf-8 -*-
{
    'name': 'Dynamic Product Category Page',
    'version': '19.0.1.0.0',
    'category': 'Website',
    'summary': 'Dynamic product category showcase on website',
    'description': """
        Dynamic Product Category Page
        ==============================
        This module extends the website category page to dynamically display
        product categories from Odoo inventory with images and descriptions.

        Features:
        ---------
        * Auto-fetch categories from product.public.category
        * Display category images and descriptions
        * Auto-scrolling category tabs
        * Responsive design
        * Direct links to shop pages
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'website',
        'product',
        'website_sale',
    ],
    'data': [
        'views/website_category_template.xml',
        'views/website_sale_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
