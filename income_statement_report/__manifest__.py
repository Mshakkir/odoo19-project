# -*- coding: utf-8 -*-
{
    'name': 'Income Statement Report',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Custom Income Statement / Profit & Loss Report with Wizard',
    'description': """
        Custom Income Statement Report module for Odoo 19 CE.
        - Select Branch/Company
        - Set Date Range (From / To)
        - Show Income, Expenses, COGS, Net Profit/Loss
        - Print PDF Report
    """,
    'author': 'Custom Development',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/income_statement_wizard_view.xml',
        'report/income_statement_report_template.xml',
        'report/income_statement_report_action.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}