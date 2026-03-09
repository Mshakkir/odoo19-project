from odoo import models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_quotation_send(self):
        """Override to open our custom send wizard (like invoice send wizard)."""

        self.ensure_one()

        self.filtered(
            lambda so: so.state in ('draft', 'sent')
        ).order_line._validate_analytic_distribution()

        # Create wizard record
        wizard = self.env['sale.order.send.wizard'].create({
            'order_id': self.id,
        })

        # Get the form view
        form_view = self.env.ref(
            'sale_quotation_send_fix.sale_order_send_wizard_form',
            raise_if_not_found=False,
        )

        return {
            'name': _('Send'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sale.order.send.wizard',
            'res_id': wizard.id,
            'views': [(form_view.id if form_view else False, 'form')],
            'view_id': form_view.id if form_view else False,
            'target': 'new',
            'context': self.env.context,
        }
