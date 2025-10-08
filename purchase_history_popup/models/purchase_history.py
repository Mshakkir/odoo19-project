from odoo import models

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def open_purchase_history_popup(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase History',
            'res_model': 'purchase.history.popup.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('purchase_history_popup.view_purchase_history_popup_wizard').id,
            'target': 'new',
            'context': {'active_id': self.id},
        }
