from odoo import models, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_rfq_send(self):
        """Override to open custom send wizard — fixes missing ir.ui.view(303) error.
        Called for Send RFQ (send_rfq=True) and Send PO (send_rfq=False).
        """
        self.ensure_one()

        # Context tells us if this is RFQ send or PO send
        is_send_rfq = self.env.context.get('send_rfq', True)

        wizard = self.env['purchase.order.send.wizard'].create({
            'order_id': self.id,
            'is_send_rfq': is_send_rfq,
        })

        form_view = self.env.ref(
            'purchase_send_fix.purchase_order_send_wizard_form',
            raise_if_not_found=False,
        )

        doc_label = _('Send RFQ') if is_send_rfq else _('Send PO')

        return {
            'name': doc_label,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'purchase.order.send.wizard',
            'res_id': wizard.id,
            'views': [(form_view.id if form_view else False, 'form')],
            'view_id': form_view.id if form_view else False,
            'target': 'new',
            'context': self.env.context,
        }