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
        Override create to prevent duplicate follower errors.
        Before creating, check if followers already exist and skip them.
        """
        if not isinstance(vals_list, list):
            vals_list = [vals_list]

        # Filter out vals that would create duplicates
        filtered_vals = []
        existing_followers = self.browse()

        for vals in vals_list:
            res_model = vals.get('res_model')
            res_id = vals.get('res_id')
            partner_id = vals.get('partner_id')

            if res_model and res_id and partner_id:
                # Check if this follower already exists
                existing = self.sudo().search([
                    ('res_model', '=', res_model),
                    ('res_id', '=', res_id),
                    ('partner_id', '=', partner_id)
                ], limit=1)

                if existing:
                    _logger.info(
                        'Follower already exists for %s(%s), partner %s. Skipping creation.',
                        res_model, res_id, partner_id
                    )
                    existing_followers |= existing
                else:
                    # Safe to create this one
                    filtered_vals.append(vals)
            else:
                # No risk of duplicate, keep it
                filtered_vals.append(vals)

        # Create only the non-duplicate followers
        new_followers = self.browse()
        if filtered_vals:
            try:
                new_followers = super(MailFollowers, self).create(filtered_vals)
            except IntegrityError as e:
                # Last resort - if somehow a duplicate still gets through
                error_message = str(e)
                if 'mail_followers' in error_message and 'duplicate key' in error_message:
                    _logger.warning('Duplicate follower error during create: %s', error_message)
                    # Return empty recordset to avoid breaking the transaction
                    return self.browse()
                else:
                    raise

        # Return combination of new and existing followers
        return new_followers | existing_followers