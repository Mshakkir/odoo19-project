{
    'name': 'Quotation Customer Balance',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Display customer balance on quotation form',
    'description': """
        Shows customer balance information (amount to pay and amount paid) 
        on the quotation form when a customer is selected.
    """,
    'depends': ['sale_management', 'account'],  # Added 'account' here
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}