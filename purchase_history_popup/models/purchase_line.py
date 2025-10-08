from odoo import models

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def open_purchase_history_popup(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase History',
            'res_model': 'purchase.history.popup.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id},
        }
