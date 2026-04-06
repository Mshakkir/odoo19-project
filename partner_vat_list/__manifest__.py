{
    'name': 'Partner VAT List + Currency (Sales & Purchase)',
    'version': '19.0.2.0.0',
    'summary': 'Sales/Purchase VAT lists, Sales Currency and hide Pricelist on partner form. Auto-apply on orders/invoices.',
    'description': '''
        Features
        --------
        Partner Form → Sales & Purchase tab:

        SALES section
          • Sales VAT List  — many2many taxes (sale-type).  Auto-applied to Sale Order
            and Customer Invoice lines when the partner is selected and a product is added.
          • Sales Currency  — default res.currency for this customer.  Auto-applied to
            the Sale Order currency (and manual rate auto-filled) when the partner is
            selected.  Works together with the custom_sale_order module currency fields.
          • Pricelist field is HIDDEN (replaced with invisible field).

        PURCHASE section
          • Purchase VAT List — many2many taxes (purchase-type).  Auto-applied to
            Purchase Order and Vendor Bill lines when the partner is selected and a
            product is added.

        Dependencies
        ------------
        Requires: base, account, sale, purchase
        Integrates with: custom_sale_order module (sale_currency_id, manual_currency_rate)
    ''',
    'author': 'Custom Development',
    'category': 'Accounting/Sales',
    'depends': [
        'base',
        'account',
        'sale',
        'purchase',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
