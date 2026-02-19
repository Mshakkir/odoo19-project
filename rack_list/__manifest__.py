{
    'name': 'Rack List',
    'version': '19.0.1.0.0',
    'summary': 'Display all products with their exact stock locations under Sales menu',
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
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}