{
    'name': 'Custom Header Footer Theme',
    'version': '1.0.0',
    'category': 'Website/Website',
    'sequence': 100,
    'summary': 'Custom header/footer colors and hide sign in button',
    'description': """
Custom Header Footer Theme Module
==================================
This module provides:
    * Custom header background color (#2c3e50)
    * Custom footer background color (#34495e)
    * Hides the sign-in/login button from header
    * White text styling for header
    * Blue accent colors for links
    * Responsive design support
    """,
    'author': 'Your Company',
    'website': 'https://www.yourwebsite.com',
    'depends': [
        'website',
        'web',
    ],
    'data': [
        'views/website_templates.xml',
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