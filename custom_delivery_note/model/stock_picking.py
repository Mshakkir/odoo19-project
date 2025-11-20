from odoo import models, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    awb_number = fields.Char(
        string="AWB Number",
        related='sale_id.awb_number',
        store=True
    )
