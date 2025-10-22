from odoo import api, fields, models

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")

    @api.model
    def create(self, vals):
        if 'move_id' in vals:
            move = self.env['account.move'].browse(vals['move_id'])
            if move.move_type in ['out_invoice', 'out_refund']:  # Customer invoice/refund
                line_vals = vals.get('product_id')
                if line_vals:
                    product = self.env['product.product'].browse(vals['product_id'])
                    if product and product.warehouse_id:
                        vals['warehouse_id'] = product.warehouse_id.id
            elif move.move_type in ['in_invoice', 'in_refund']:  # Vendor bills
                line_vals = vals.get('product_id')
                if line_vals:
                    product = self.env['product.product'].browse(vals['product_id'])
                    if product and product.warehouse_id:
                        vals['warehouse_id'] = product.warehouse_id.id
        return super(AccountMoveLine, self).create(vals)
