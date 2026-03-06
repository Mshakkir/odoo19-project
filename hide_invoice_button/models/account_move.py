# -*- coding: utf-8 -*-
from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _notify_get_action_link(self, link_type, **kwargs):
        """
        Override to suppress the 'View Invoice' button in email notifications.

        In Odoo 19, account_move.py (~line 5992) calls:
            access_link = self._notify_get_action_link('view', access_token=self.access_token)
            button_access = {'url': access_link} if access_link else {}

        By returning an empty string for 'view' links on invoices/bills,
        button_access becomes {} and Odoo skips rendering the View Invoice button.
        """
        # Only suppress the button for customer invoices and vendor bills
        if link_type == 'view' and self.move_type in (
            'out_invoice',   # Customer Invoice
            'out_refund',    # Customer Credit Note
            'in_invoice',    # Vendor Bill
            'in_refund',     # Vendor Credit Note
        ):
            return ''

        return super()._notify_get_action_link(link_type, **kwargs)
