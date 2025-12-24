# -*- coding: utf-8 -*-

from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _message_auto_subscribe_followers(self, updated_values, default_subtype_ids):
        """Override to prevent duplicate follower subscription"""
        # Don't auto-subscribe if partner is already following
        new_partners = super()._message_auto_subscribe_followers(updated_values, default_subtype_ids)

        result = []
        for partner_id, subtype_ids, active in new_partners:
            # Check if this partner is already following this record
            if self and not self.message_partner_ids.filtered(lambda p: p.id == partner_id):
                result.append((partner_id, subtype_ids, active))

        return result

    def message_subscribe(self, partner_ids=None, subtype_ids=None):
        """Override to handle duplicate follower gracefully"""
        if not partner_ids:
            return True

        # Filter out partners that are already following
        existing_partner_ids = self.message_partner_ids.ids
        new_partner_ids = [pid for pid in partner_ids if pid not in existing_partner_ids]

        if new_partner_ids:
            return super(PosOrder, self).message_subscribe(partner_ids=new_partner_ids, subtype_ids=subtype_ids)

        return True