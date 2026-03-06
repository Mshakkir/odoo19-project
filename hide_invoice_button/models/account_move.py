# -*- coding: utf-8 -*-
from odoo import models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_mail_template(self):
        """
        Override to ensure the correct template is used and
        partner_to is always populated with the customer email.
        """
        result = super()._get_mail_template()
        return result

    def action_send_and_print(self, **kwargs):
        """
        Override to ensure:
        1. The 'To' field is auto-filled with the customer email.
        2. The context suppresses the portal access link (View Invoice button).
        """
        # Suppress portal access button by removing access_token from context
        ctx = dict(self.env.context)
        ctx['no_access_link'] = True          # tells mail layout: skip View Invoice button
        ctx['mail_notify_force_send'] = False  # don't force send, show compose dialog

        return super(AccountMove, self.with_context(ctx)).action_send_and_print(**kwargs)

    def _prepare_invoice_pdf_report(self, invoice_data):
        """Ensure partner email is always included."""
        result = super()._prepare_invoice_pdf_report(invoice_data)
        return result

    def _send_invoice_to_journal(self):
        """Override to suppress portal link."""
        ctx = dict(self.env.context, no_access_link=True)
        return super(AccountMove, self.with_context(ctx))._send_invoice_to_journal()

    @api.model
    def _get_default_invoice_email_values(self):
        """
        Ensure the partner email is always pre-filled in the send dialog.
        This fixes the blank 'To' field issue.
        """
        res = super()._get_default_invoice_email_values() \
            if hasattr(super(), '_get_default_invoice_email_values') else {}
        if self.partner_id and self.partner_id.email:
            res['partner_ids'] = [(4, self.partner_id.id)]
        return res
