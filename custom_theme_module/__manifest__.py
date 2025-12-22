{
    'name': 'Custom Header Footer Theme',
    'version': '1.0.0',
    'category': 'Website',
    'summary': 'Customize header/footer colors and hide sign in button',
    'description': """
        Custom module to:
        - Change header and footer color themes
        - Hide the default sign in button
        - Apply custom styling to website
    """,
    'author': 'Your Name',
    'website': 'https://www.yourwebsite.com',
    'depends': ['website', 'web'],
    'data': [
        'views/templates.xml',
        'views/header_footer_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'custom_theme_module/static/src/css/custom_style.css',
            'custom_theme_module/static/src/js/custom_header.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}