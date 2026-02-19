{
    'name': 'Rack List',
    'version': '19.0.1.0.0',
    'summary': 'Display all products with their exact stock locations under Sales menu',
    'description': """
        Adds a "Rack List" menu item in the Sales top bar that displays
        all products along with their exact storage locations and quantities.
        Includes OWL-powered Sort By buttons (Product / Location / Qty).
    """,
    'author': 'Custom',
    'category': 'Sales',
    'depends': ['sale_management', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/rack_list_views.xml',
        'views/rack_list_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'rack_list/static/src/js/rack_list_controller.js',
            'rack_list/static/src/xml/rack_list_templates.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}