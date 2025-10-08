from odoo import models

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def open_purchase_history_popup(self):
        # Sample action (replace with yours as needed)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase History',
            'res_model': 'purchase.history.popup.wizard',  # Or the wizard model's name you are using
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id},
        }
