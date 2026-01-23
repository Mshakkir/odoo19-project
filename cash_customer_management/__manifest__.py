{
    'name': 'Cash Customer Management',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Manage walk-in customers with single ledger account',
    'description': """
        This module allows you to:
        - Use a single 'Cash Customer' for all walk-in sales
        - Capture actual customer details in custom fields
        - Print customer name and address on invoice
        - Keep your ledger clean and organized
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['sale_management', 'account'],
    'data': [
        'data/cash_customer_data.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'reports/invoice_report_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}