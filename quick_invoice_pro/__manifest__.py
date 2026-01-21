# -*- coding: utf-8 -*-
{
    'name': 'Quick Invoice Pro',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Fast invoice creation with smart controls for walk-in customers',
    'description': """
Quick Invoice Pro
=================
Features:
- One-click invoice creation from sale orders
- Smart approval workflow (threshold-based)
- Real-time stock availability checks
- Integrated payment recording
- Quick return/refund handling
- Draft invoice option for modifications
- Configurable settings per company
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'sale_management',
        'stock',
        'account',
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/default_settings.xml',

        # Views
        'views/quick_invoice_menu.xml',
        'views/sale_order_views.xml',
        'views/res_config_settings_views.xml',

        # Wizards
        'wizards/quick_invoice_wizard_views.xml',
        'wizards/quick_payment_wizard_views.xml',
        'wizards/quick_return_wizard_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}