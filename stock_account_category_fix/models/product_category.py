from odoo import fields, models

class ProductCategory(models.Model):
    _inherit = 'product.category'

    property_stock_valuation_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Stock Valuation Account',
        company_dependent=True,
    )
    property_stock_journal = fields.Many2one(
        comodel_name='account.journal',
        string='Stock Journal',
        company_dependent=True,
    )
    property_stock_account_input_categ_id = fields.Many2one(
        comodel_name='account.account',
        string='Stock Input Account',
        company_dependent=True,
    )
    property_stock_account_output_categ_id = fields.Many2one(
        comodel_name='account.account',
        string='Stock Output Account',
        company_dependent=True,
    )
