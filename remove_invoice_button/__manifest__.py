{
    'name': 'Remove Invoice Button from Email',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': ['account', 'mail'],
    'data': [
        'views/email_template_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'external_dependencies': {
        'python': [],
    }
}