# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

    property_stock_valuation_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Stock Valuation Account',
        company_dependent=True,
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'asset_cash', 'liability_credit_card')), ('deprecated', '=', False)]",
        help="When automated inventory valuation is enabled on a product, "
             "this account will hold the current value of the products.",
    )
    property_stock_journal = fields.Many2one(
        comodel_name='account.journal',
        string='Stock Journal',
        company_dependent=True,
        help="When doing real-time inventory valuation, this is the Accounting "
             "Journal in which entries will be automatically posted when stock "
             "moves are processed.",
    )
    property_stock_account_input_categ_id = fields.Many2one(
        comodel_name='account.account',
        string='Stock Input Account',
        company_dependent=True,
        domain="[('deprecated', '=', False)]",
        help="When doing real-time inventory valuation, counterpart journal "
             "items for all incoming stock moves will be posted in this account, "
             "unless there is a specific valuation account set on the source location.",
    )
    property_stock_account_output_categ_id = fields.Many2one(
        comodel_name='account.account',
        string='Stock Output Account',
        company_dependent=True,
        domain="[('deprecated', '=', False)]",
        help="When doing real-time inventory valuation, counterpart journal "
             "items for all outgoing stock moves will be posted in this account, "
             "unless there is a specific valuation account set on the destination location.",
    )
