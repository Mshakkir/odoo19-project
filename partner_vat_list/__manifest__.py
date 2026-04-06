# -*- coding: utf-8 -*-
{
    'name': 'Partner VAT List - Auto Tax Selection',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Add VAT list on partner form and auto-select tax on order/invoice lines',
    'description': """
Partner VAT List
================
- Adds a VAT/Tax list on Customer/Vendor form view
- When a product is selected on Sale Order, Purchase Order or Invoice line,
  the tax is automatically set based on the partner's configured VAT list.
- Supports tax mapping per product category or specific product
    """,
    'author': 'Custom Development',
    'depends': [
        'base',
        'account',
        'sale_management',
        'purchase',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/partner_vat_list_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
