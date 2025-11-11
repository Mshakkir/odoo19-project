{
    'name': 'Sale AWB Field',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Add AWB Number field to Sales and Invoices',
    'description': """
        Add Air Waybill (AWB) Number Field
        ===================================

        * Adds AWB Number field to Sale Orders
        * Adds AWB Number field to Invoices
        * Auto-transfers AWB from Sale Order to Invoice
    """,
    'author': 'Your Name',
    'depends': [
        'sale_management',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}