{
    'name': 'Sale Quotation Send Wizard',
    'version': '19.0.1.0.0',
    'summary': 'Modern Send wizard for Sale Quotations (like invoice send)',
    'category': 'Sales',
    'depends': ['sale', 'mail', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/sale_order_send_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
