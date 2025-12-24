# -*- coding: utf-8 -*-

from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _message_get_default_recipients(self):
        """Prevent duplicate followers on POS orders"""
        # Check if followers already exist before adding
        res = {}
        for order in self:
            # Get existing followers
            existing_partner_ids = order.message_partner_ids.ids

            # Only add partner if not already following
            if order.partner_id and order.partner_id.id not in existing_partner_ids:
                res[order.id] = {
                    'partner_ids': [order.partner_id.id],
                    'email_to': False,
                    'email_cc': False
                }
            else:
                res[order.id] = {
                    'partner_ids': [],
                    'email_to': False,
                    'email_cc': False
                }
        return res