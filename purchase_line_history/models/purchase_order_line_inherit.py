from odoo import models, fields

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def action_stock_history(self):
        """ Open stock moves related to this product """
        self.ensure_one()
        return {
            'name': 'Stock History',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.product_id.id)],
        }

    def action_sale_history(self):
        """ Open sale order lines related to this product """
        self.ensure_one()
        return {
            'name': 'Sale History',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.line',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.product_id.id)],
        }

    def action_purchase_history(self):
        """ Open purchase order lines related to this product """
        self.ensure_one()
        return {
            'name': 'Purchase History',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.line',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.product_id.id)],
        }
