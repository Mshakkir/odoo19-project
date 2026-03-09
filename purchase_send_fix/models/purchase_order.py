from odoo import models, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_rfq_send(self):
        """Override to open our custom send wizard (fixes missing view 303 error)."""
        return self._open_send_wizard()

    def action_send_rfq(self):
        """Override alternative method name used in some Odoo versions."""
        return self._open_send_wizard()

    def _open_send_wizard(self):
        self.ensure_one()

        wizard = self.env['purchase.order.send.wizard'].create({
            'order_id': self.id,
        })

        form_view = self.env.ref(
            'purchase_send_fix.purchase_order_send_wizard_form',
            raise_if_not_found=False,
        )

        return {
            'name': _('Send'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'purchase.order.send.wizard',
            'res_id': wizard.id,
            'views': [(form_view.id if form_view else False, 'form')],
            'view_id': form_view.id if form_view else False,
            'target': 'new',
            'context': self.env.context,
        }
