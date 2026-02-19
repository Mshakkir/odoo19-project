{
    'name': 'Rack List',
    'version': '19.0.1.0.0',
    'summary': 'Display all products with their exact stock locations under Sales menu',
    'description': """
        Adds a "Rack List" menu item in the Sales top bar that displays
        all products along with their exact storage locations and quantities.
        Includes OWL-powered Product and Location filter inputs.
    """,
    'author': 'Custom',
    'category': 'Sales',
    'depends': ['sale_management', 'stock', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/rack_list_views.xml',
        'views/rack_list_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'rack_list/static/src/css/rack_list_filter_bar.css',
            # XML MUST be bundled AFTER web's list_controller.xml so that
            # OWL can resolve t-inherit="web.ListController" at runtime.
            ('after', 'web/static/src/views/list/list_controller.xml',
             'rack_list/static/src/xml/rack_list_filter_bar.xml'),
            # JS component file must come after the XML templates are registered.
            ('after', 'rack_list/static/src/xml/rack_list_filter_bar.xml',
             'rack_list/static/src/js/rack_list_filter_bar.js'),
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}