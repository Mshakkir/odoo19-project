{
    'name': 'Custom Purchase Order Report',
    'version': '1.0',
    'depends': ['purchase', 'base','custom_sa_quotation'],
    'data': [
        'report/report.xml',
        'report/report_purchase_order.xml',
    ],
    'installable': True,
    'application': False,
}
