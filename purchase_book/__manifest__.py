{
    'name': 'Purchase Book Reports',
    'version': '19.0.1.0.0',
    'category': 'Purchases',
    'summary': 'Purchase Book, Purchase Return & Combined Reports for Saudi Trading',
    'description': """
        Custom Purchase Book Reports Module
        ====================================
        * Purchase Report
        * Purchase Return Report
        * Purchase & Purchase Return Combined Report
        * Date range filtering
        * Short/Detail view options
        * VAT compliant for Saudi Arabia
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['purchase', 'account', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/purchase_book_wizard_view.xml',
        'report/purchase_book_report.xml',
        'report/purchase_book_templates.xml',
        'views/purchase_book_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}