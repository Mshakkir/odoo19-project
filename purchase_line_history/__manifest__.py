{
    'name': 'Purchase Line History',
    'version': '1.0',
    'summary': 'Add Stock, Sale, Purchase history buttons to RFQ product lines',
    'description': """
        Adds three buttons to RFQ product lines:
        - Stock History
        - Sale History
        - Purchase History
    """,
    'author': 'Your Name',
    'category': 'Purchase',
    'depends': ['purchase', 'sale', 'stock'],
    'data': [
        'views/purchase_order_form_inherit.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
