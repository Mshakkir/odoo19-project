{
    'name': 'Purchase Reports',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'depends': ['purchase', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/purchase_report_by_product_wizard.xml',
        'views/purchase_report_views.xml',
        'views/purchase_report_menus.xml',
    ],
    'installable': True,
    'application': False,
}