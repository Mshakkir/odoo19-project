{
    'name': 'Partner VAT List (Sales & Purchase)',
    'version': '19.0.1.0.0',
    'summary': 'Add Sales VAT and Purchase VAT dropdown lists on partner form, auto-apply on order/invoice lines',
    'description': '''
        - Adds a "Sales VAT List" many2many field (account.tax) on the partner form → Sales & Purchase tab → Sales section
        - Adds a "Purchase VAT List" many2many field (account.tax) on the partner form → Sales & Purchase tab → Purchase section
        - When a customer/vendor is selected on Sale Order, Purchase Order, or Invoice, and a product is added to order lines,
          the configured VAT taxes from the partner are automatically applied to the line instead of the product default taxes.
    ''',
    'author': 'Custom Development',
    'category': 'Accounting/Accounting',
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
