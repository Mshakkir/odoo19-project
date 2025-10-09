from odoo import models, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Button: View Product Stock
    def action_view_stock_history(self):
        self.ensure_one()
        product_ids = self.order_line.mapped('product_id').ids
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Moves',
            'res_model': 'stock.move',
            'view_mode': 'tree,form',
            'domain': [('product_id', 'in', product_ids)],
            'context': {'create': False},
        }

    # Button: View Product Sales History
    def action_view_sales_history(self):
        self.ensure_one()
        product_ids = self.order_line.mapped('product_id').ids
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales History',
            'res_model': 'sale.order.line',
            'view_mode': 'tree,form',
            'domain': [('product_id', 'in', product_ids)],
            'context': {'create': False},
        }

    # Button: View Product Purchase History
    def action_view_purchase_history(self):
        self.ensure_one()
        product_ids = self.order_line.mapped('product_id').ids
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase History',
            'res_model': 'purchase.order.line',
            'view_mode': 'tree,form',
            'domain': [('product_id', 'in', product_ids), ('order_id.state', '=', 'purchase')],
            'context': {'create': False},
        }
