from odoo import models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_quotation_send(self):
        """Override to force the standard email compose form view
        instead of the old mail template wizard view."""

        self.filtered(
            lambda so: so.state in ('draft', 'sent')
        ).order_line._validate_analytic_distribution()

        ctx = {
            'default_model': 'sale.order',
            'default_res_ids': self.ids,
            'default_composition_mode': 'comment',
            'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
            'email_notification_allow_footer': True,
            'hide_mail_template_management_options': True,
            'proforma': self.env.context.get('proforma', False),
        }

        if len(self) > 1:
            ctx['default_composition_mode'] = 'mass_mail'
        else:
            ctx['force_email'] = True
            if not self.env.context.get('hide_default_template'):
                mail_template = self._find_mail_template()
                if mail_template:
                    ctx['default_template_id'] = mail_template.id
                    ctx['mark_so_as_sent'] = True
            else:
                for order in self:
                    order._portal_ensure_token()

        # Force the standard compose form (To/Subject fields style)
        compose_form = self.env.ref(
            'mail.email_compose_message_wizard_form',
            raise_if_not_found=False
        )

        action = {
            'name': _('Send'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id if compose_form else False, 'form')],
            'view_id': compose_form.id if compose_form else False,
            'target': 'new',
            'context': ctx,
        }

        # Check document layout (admin check for company logo)
        if (
            self.env.context.get('check_document_layout')
            and not self.env.context.get('discard_logo_check')
            and self.env.is_admin()
            and not self.env.company.external_report_layout_id
        ):
            layout_action = self.env['ir.actions.report']._action_configure_external_report_layout(
                action,
            )
            action.pop('close_on_report_download', None)
            layout_action['context']['dialog_size'] = 'extra-large'
            return layout_action

        return action
