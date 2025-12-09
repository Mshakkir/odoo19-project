{
    'name': 'Custom Payment Receipt Header',
    'version': '1.0',
    'license': 'LGPL-3',
    'author': 'Your Name',
    'summary': 'Customize the header of Vendor Payment Receipt in Odoo 19 CE',
    'depends': ['account'],
    'data': [
        'views/payment_receipt_inherit.xml',
    ],
    'installable': True,
}
