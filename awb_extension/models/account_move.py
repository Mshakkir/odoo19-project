from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    awb_number = fields.Char(string="Air Waybill No.")
    carrier_name = fields.Char(string="Carrier")

    @api.model
    def create(self, vals):
        move = super(AccountMove, self).create(vals)
        # Auto-copy AWB from related Delivery Order
        if move.invoice_origin:
            picking = self.env['stock.picking'].search(
                [('origin', '=', move.invoice_origin)],
                limit=1
            )
            if picking:
                move.awb_number = picking.awb_number
                move.carrier_name = picking.carrier_name
        return move
