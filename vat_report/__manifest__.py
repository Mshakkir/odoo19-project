{
    'name': 'vat report',
    'version': '1.0.2',
    'category': 'Invoicing Management',
    'description': 'Accounting Reports For Odoo 19, Accounting Financial Reports, '
                   'Odoo 19 Financial Reports',
    'summary': 'Accounting Reports For Odoo 19',
    'sequence': '1',
    'author': 'Odoo Mates, Odoo SA',
    'license': 'LGPL-3',
    'company': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'website': 'https://www.youtube.com/watch?v=yA4NLwOLZms',
    'depends': ['account'],
    'live_test_url': 'https://www.youtube.com/watch?v=yA4NLwOLZms',
    'data': [
        'views/tax_detail_view.xml',
        'report/report_tax_detailed.xml'
    ],
    "installable": True,

}
