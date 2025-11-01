{
    'name': 'Analytic Account Automation',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Automatic Analytic Account Propagation from SO/PO to Invoice/Bill',
    'description': '''
        Automatic Analytic Account Assignment
        =====================================
        * Automatically copy analytic accounts from Sales Order to Invoice
        * Automatically copy analytic accounts from Purchase Order to Bill
        * Works for all journal items (Debit and Credit lines)
        * No manual entry needed in Journal Items tab
    ''',
    'depends': ['sale', 'purchase', 'account', 'analytic'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}