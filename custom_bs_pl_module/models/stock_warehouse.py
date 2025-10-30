# models/stock_warehouse.py
from odoo import models, fields

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string="Analytic Account",
        help="Link this warehouse to an analytic account for reporting."
    )
