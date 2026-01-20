{
    'name': 'Partner Balance - Complete Module',
    'version': '19.0.1.0.0',
    'category': 'Sales/Purchase/Accounting/Inventory',
    'summary': 'Display customer/vendor balance across all modules',
    'description': """
        Shows customer/vendor balance information across multiple modules:

        Features:
        - Sales Orders: Customer balance (Total Invoiced, Amount Paid, Balance Due)
        - Purchase Orders: Vendor balance (Total Billed, Amount Paid, Balance Due)
        - Customer Invoices: Customer balance with clickable links
        - Vendor Bills: Vendor balance with clickable links
        - Customer Payments: Partner balance information
        - Vendor Payments: Partner balance information
        - Delivery Orders: Customer balance for outgoing shipments
        - Receipts: Vendor balance for incoming shipments

        All fields are clickable to view related documents (invoices, bills, payments).

        Compatible with Odoo Mates Accounting module for Odoo 19 CE.
    """,
    'depends': [
        'sale_management',
        'purchase',
        'om_account_accountant',
        'stock',
    ],
    'data': [
        'views/sale_order_views.xml',
        'views/purchase_order_view.xml',
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}