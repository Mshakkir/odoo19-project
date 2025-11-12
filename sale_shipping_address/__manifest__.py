{
    'name': 'Sale Shipping Address',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Add Shipping To field in Quotation/Sales Order',
    'depends': ['sale', 'account', 'my_invoice_custom'],
    'data': [
        'views/sale_order_views.xml',
        'reports/invoice_report_inherit.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}