{
    'name': 'Purchase Reports',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'depends': ['purchase', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_report_views.xml',
        'views/purchase_report_menus.xml',
        'wizard/purchase_report_by_product_wizard.xml',
    ],
    'installable': True,
    'application': False,
}