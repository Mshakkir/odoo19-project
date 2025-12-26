# -*- coding: utf-8 -*-

from odoo import models, api
from psycopg2 import IntegrityError
import logging

_logger = logging.getLogger(__name__)


class MailFollowers(models.Model):
    _inherit = 'mail.followers'

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to catch duplicate follower errors.
        Instead of failing, we search for and return existing followers.
        """
        try:
            return super(MailFollowers, self).create(vals_list)
        except IntegrityError as e:
            error_message = str(e)
            if 'mail_followers_unique_idx' in error_message or \
                    'duplicate key' in error_message or \
                    'mail_followers_res_partner_res_model_id_uniq' in error_message:

                _logger.info(
                    'Duplicate follower detected during create. '
                    'Returning existing followers instead. Error: %s',
                    error_message
                )

                # Clear the error from the transaction
                self.env.cr.rollback()

                # Search for existing followers matching the vals_list
                if not isinstance(vals_list, list):
                    vals_list = [vals_list]

                existing_followers = self.env['mail.followers'].browse()

                for vals in vals_list:
                    res_model = vals.get('res_model')
                    res_id = vals.get('res_id')
                    partner_id = vals.get('partner_id')

                    if res_model and res_id and partner_id:
                        # Search for existing follower
                        existing = self.search([
                            ('res_model', '=', res_model),
                            ('res_id', '=', res_id),
                            ('partner_id', '=', partner_id)
                        ], limit=1)

                        if existing:
                            _logger.info(
                                'Found existing follower: model=%s, id=%s, partner=%s',
                                res_model, res_id, partner_id
                            )
                            existing_followers |= existing
                        else:
                            _logger.warning(
                                'No existing follower found for: model=%s, id=%s, partner=%s. '
                                'This might cause issues.',
                                res_model, res_id, partner_id
                            )

                # Return existing followers, or empty recordset if none found
                return existing_followers if existing_followers else self.browse()
            else:
                # Re-raise if it's a different IntegrityError
                raise