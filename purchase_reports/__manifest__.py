{
    'name': 'Purchase Reports',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'depends': ['purchase', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/purchase_report_by_product_wizard.xml',  # Load wizard FIRST (contains action)
        'views/purchase_report_views.xml',
        'views/purchase_report_menus.xml',  # Load menu LAST (references action)
    ],
    'installable': True,
    'application': False,
}