{
    'name': 'Invoice Date Filter',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Add date range filter button for invoices',
    'description': """
        This module adds a custom date range filter button in invoice list view.
        Users can filter invoices by selecting from and to dates.
    """,
    'author': 'Your Name',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/invoice_date_filter_wizard_views.xml',
        'views/account_move_views.xml',
        'views/account_move_search_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
