from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_quotation_send(self):
        """Override to use the modern mail composer (comment mode)
        with proper To field, matching the invoice send wizard style."""

        self.ensure_one()

        # Find the 'Sales: Send Quotation' email template
        template = self.env.ref(
            'sale.email_template_edi_sale', raise_if_not_found=False
        )

        ctx = {
            'default_model': 'sale.order',
            'default_res_ids': self.ids,
            'default_composition_mode': 'comment',
            'default_email_layout_xmlid': (
                'mail.mail_notification_layout_with_responsible_and_action'
            ),
            'default_template_id': template.id if template else False,
            'force_email': True,
            'mark_so_as_sent': True,
            'proforma': self.env.context.get('proforma', False),
        }

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }
