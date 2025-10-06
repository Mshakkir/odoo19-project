from odoo import models, api

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def action_view_product_history(self):
        """Open wizard with stock, purchase, and sales history for this product"""
        self.ensure_one()
        return {
            'name': 'Product History',
            'type': 'ir.actions.act_window',
            'res_model': 'product.history.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_product_id': self.product_id.id},
        }
