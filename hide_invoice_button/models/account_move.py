# -*- coding: utf-8 -*-
from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        """
        Override to completely hide the 'View Invoice' button from email notifications.

        In Odoo 19, account_move.py lines 5992-6002:
            access_link = self._notify_get_action_link('view', access_token=self.access_token)
            button_access = {'url': access_link} if access_link else {}
            recipient_group = (
                'additional_intended_recipient', ...,
                {
                    'has_button_access': True,   <-- this renders the button
                    'button_access': button_access,
                }
            )

        We call super() then force has_button_access=False on ALL groups
        so the button is completely hidden (not just unclickable).
        """
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )

        # Only suppress for invoices/bills, not plain journal entries
        if self.move_type == 'entry':
            return groups

        # Set has_button_access=False on every group to fully hide the button
        patched = []
        for group in groups:
            if isinstance(group, (list, tuple)) and len(group) >= 3:
                group_id, condition, options = group[0], group[1], dict(group[2])
                options['has_button_access'] = False
                options['button_access'] = {}
                patched.append((group_id, condition, options))
            else:
                patched.append(group)

        return patched
