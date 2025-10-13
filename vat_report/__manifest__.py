# Copyright 2018 Forest and Biomass Romania
# Copyright 2020 ForgeFlow S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'VAT Report',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'VAT Report for Odoo 19',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'AGPL-3',
    'depends': [
        'account',
        'date_range',
        'web',
    ],
    'data': [
        'wizard/vat_report_wizard_view.xml',
        'report/vat_report_template.xml',
        'report/vat_report.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}