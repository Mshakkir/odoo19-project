# -*- coding: utf-8 -*-

from odoo import models
from psycopg2 import IntegrityError
import logging

_logger = logging.getLogger(__name__)


class MailFollowers(models.Model):
    _inherit = 'mail.followers'

    def create(self, vals_list):
        """
        Override create to catch duplicate follower errors.
        This is a safer approach that doesn't depend on internal method signatures.
        """
        try:
            return super(MailFollowers, self).create(vals_list)
        except IntegrityError as e:
            error_message = str(e)
            if 'mail_followers_unique_idx' in error_message or \
                    'duplicate key' in error_message or \
                    'mail_followers_res_partner_res_model_id_uniq' in error_message:
                _logger.warning(
                    'Duplicate follower detected during create. '
                    'Ignoring duplicate insertion. Error: %s',
                    error_message
                )
                # Rollback the failed transaction
                self.env.cr.rollback()

                # Try to return existing followers instead
                if isinstance(vals_list, dict):
                    vals_list = [vals_list]

                existing_followers = self.env['mail.followers']
                for vals in vals_list:
                    if 'res_model' in vals and 'res_id' in vals and 'partner_id' in vals:
                        existing = self.search([
                            ('res_model', '=', vals['res_model']),
                            ('res_id', '=', vals['res_id']),
                            ('partner_id', '=', vals['partner_id'])
                        ], limit=1)
                        if existing:
                            existing_followers |= existing

                return existing_followers or self.browse()
            else:
                # Re-raise if it's a different IntegrityError
                raise


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _message_auto_subscribe_followers(self, updated_values, default_subtype_ids):
        """
        Additional safety layer to catch errors during auto-subscription
        """
        try:
            return super(MailThread, self)._message_auto_subscribe_followers(
                updated_values, default_subtype_ids
            )
        except IntegrityError as e:
            if 'mail_followers' in str(e) and 'duplicate key' in str(e):
                _logger.warning(
                    'Duplicate follower in auto-subscribe. Ignoring. Error: %s',
                    str(e)
                )
                self.env.cr.rollback()
                return []
            else:
                raise