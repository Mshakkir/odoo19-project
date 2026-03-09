{
    'name': 'Purchase Order Send Wizard',
    'version': '19.0.1.0.0',
    'summary': 'Modern Send wizard for Purchase Orders / RFQ (fixes missing view error)',
    'category': 'Purchase',
    'depends': ['purchase', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/purchase_order_send_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
