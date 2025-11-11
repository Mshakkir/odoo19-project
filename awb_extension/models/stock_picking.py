from odoo import models, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    awb_number = fields.Char(string="Air Waybill No.")
    carrier_name = fields.Char(string="Carrier")
