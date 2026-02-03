#
{
    "name": "Account Fixed Discount",
    "summary": "Allows to apply fixed amount discounts in sales orders and invoices.",
    "version": "19.0.1.0.0",
    "category": "Accounting & Finance",
    "website": "https://github.com/OCA/account-invoicing",
    "author": "ForgeFlow, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": ["account", "sale_management", "sale_stock"],
    "excludes": ["account_invoice_triple_discount"],
    "data": [
        "security/res_groups.xml",
        "views/account_move_view.xml",
        "views/sale_order_view.xml",
        "reports/report_account_invoice.xml",
        "reports/report_sale_order.xml",
    ],
}
#
# {
#     "name": "Account Fixed Discount",
#     "summary": "Allows to apply fixed amount discounts in sales orders and invoices.",
#     "version": "19.0.1.0.0",
#     "category": "Accounting & Finance",
#     "website": "https://github.com/OCA/account-invoicing",
#     "author": "ForgeFlow, Odoo Community Association (OCA)",
#     "license": "AGPL-3",
#     "application": False,
#     "installable": True,
#     "depends": ["account", "sale_management"],
#     "excludes": ["account_invoice_triple_discount"],
#     "data": [
#         "security/res_groups.xml",
#         "views/account_move_view.xml",
#         "views/sale_order_views.xml",
#         "reports/report_account_invoice.xml",
#         "reports/report_sale_order.xml",
#     ],
# }

# # Copyright 2017 ForgeFlow S.L.
# # License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
#
# {
#     "name": "Account Fixed Discount",
#     "summary": "Allows to apply fixed amount discounts in sales orders and invoices.",
#     "version": "19.0.1.0.0",
#     "category": "Accounting & Finance",
#     "website": "https://github.com/OCA/account-invoicing",
#     "author": "ForgeFlow, Odoo Community Association (OCA)",
#     "license": "AGPL-3",
#     "application": False,
#     "installable": True,
#     "depends": ["account", "sale_management"],
#     "excludes": ["account_invoice_triple_discount"],
#     "data": [
#         "security/res_groups.xml",
#         "views/account_move_view.xml",
#         "reports/report_account_invoice.xml",
#     ],
# }

# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)