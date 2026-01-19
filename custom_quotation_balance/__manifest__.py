{
    'name': 'Quotation & Purchase Customer/Vendor Balance',
    'version': '19.0.1.0.0',
    'category': 'Sales/Purchase',
    'summary': 'Display customer/vendor balance on quotation and purchase order forms',
    'description': """
        Shows customer balance information on quotation forms and vendor balance on purchase orders.

        Features:
        - Customer balance on Sales Orders (Total Invoiced, Amount Paid, Balance Due)
        - Vendor balance on Purchase Orders (Total Billed, Amount Paid, Balance Due)
        - Clickable fields to view related invoices/bills and payments

        Compatible with Odoo Mates Accounting module for Odoo 19 CE.
    """,
    'depends': ['sale_management', 'purchase', 'om_account_accountant'],
    'data': [
        'views/sale_order_views.xml',
        'views/purchase_order_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}