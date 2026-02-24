# -*- coding: utf-8 -*-
{
    'name': 'Income Statement Report',
    'version': '19.0.2.0.0',
    'category': 'Accounting',
    'summary': 'Income Statement / Profit & Loss PDF Report',
    'author': 'Custom Development',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'report/income_statement_report_template.xml',
        'report/income_statement_report_action.xml',
        'wizard/income_statement_wizard_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}