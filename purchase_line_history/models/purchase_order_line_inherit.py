from odoo import models, fields, api

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # Optional: Add related field to show stock qty in RFQ line
    stock_qty = fields.Float(
        string='Available Stock',
        related='product_id.qty_available',
        readonly=True
    )

    def action_stock_history(self):
        """ Open stock moves of this product """
        return {
            'name': 'Stock History',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.product_id.id)],
        }

    def action_sale_history(self):
        """ Open sale orders lines of this product """
        return {
            'name': 'Sale History',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.line',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.product_id.id)],
        }

    def action_purchase_history(self):
        """ Open purchase order lines of this product """
        return {
            'name': 'Purchase History',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.line',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.product_id.id)],
        }
