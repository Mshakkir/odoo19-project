
{
    'name': 'Sale Order Batch Invoice from Customer',
    'version': '19.0.1.1.2',
    'category': 'Sales',
    'summary': 'Create invoices from multiple sale orders via customer invoice menu',
    'description': """
        This module allows you to create a single invoice from multiple sale orders
        by selecting them from the Accounting > Customers > Invoices menu.

        Features:
        - Select customer from invoice menu
        - View uninvoiced sale orders for that customer
        - Create batch invoice from selected orders
        - Does not affect the default sale order invoicing workflow
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['sale_management', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/sale_order_invoice_wizard_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}