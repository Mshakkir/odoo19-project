# -*- coding: utf-8 -*-

from odoo import models, api
from psycopg2 import IntegrityError
import logging

_logger = logging.getLogger(__name__)


class MailFollowers(models.Model):
    _inherit = 'mail.followers'

    @api.model
    def _add_followers(self, res_model, res_ids, partner_ids, subtypes=None, customer_ids=None, check_existing=True):
        """
        Override _add_followers to skip partners that are already following.
        This prevents the duplicate key error from happening in the first place.
        Works for ALL models (account.move, stock.picking, sale.order, etc.)
        """
        if partner_ids:
            # Always check for existing followers to prevent duplicates
            # Get existing followers for these records
            existing = self.sudo().search([
                ('res_model', '=', res_model),
                ('res_id', 'in', res_ids),
                ('partner_id', 'in', partner_ids)
            ])

            if existing:
                existing_partners = set(existing.mapped('partner_id').ids)

                # Filter out partners that are already following
                original_count = len(partner_ids)
                partner_ids = [pid for pid in partner_ids if pid not in existing_partners]

                if original_count > len(partner_ids):
                    _logger.info(
                        'Skipped %d duplicate follower(s) for %s(%s)',
                        original_count - len(partner_ids), res_model, res_ids
                    )

                if not partner_ids:
                    _logger.info(
                        'All partners already following %s(%s), returning existing followers',
                        res_model, res_ids
                    )
                    return existing

        # Call parent method with filtered partner_ids
        try:
            return super(MailFollowers, self)._add_followers(
                res_model=res_model,
                res_ids=res_ids,
                partner_ids=partner_ids,
                subtypes=subtypes,
                customer_ids=customer_ids,
                check_existing=check_existing
            )
        except IntegrityError as e:
            # Extra safety net in case duplicates still slip through
            error_message = str(e)
            if 'mail_followers' in error_message and 'duplicate key' in error_message:
                _logger.warning(
                    'IntegrityError caught for %s(%s): %s. Searching for existing followers.',
                    res_model, res_ids, error_message
                )
                # Don't rollback - just search for existing
                existing = self.sudo().search([
                    ('res_model', '=', res_model),
                    ('res_id', 'in', res_ids),
                    ('partner_id', 'in', partner_ids)
                ])
                return existing if existing else self.browse()
            else:
                raise

    @api.model_create_multi
    def create(self, vals_list):
        """
        Additional safety layer at create level
        """
        try:
            return super(MailFollowers, self).create(vals_list)
        except IntegrityError as e:
            error_message = str(e)
            if 'mail_followers_unique_idx' in error_message or \
                    'duplicate key' in error_message or \
                    'mail_followers_res_partner_res_model_id_uniq' in error_message:

                _logger.warning(
                    'Duplicate follower in create(). Searching for existing. Error: %s',
                    error_message
                )

                # Search for existing followers instead of creating
                if not isinstance(vals_list, list):
                    vals_list = [vals_list]

                existing_followers = self.env['mail.followers'].browse()

                for vals in vals_list:
                    if 'res_model' in vals and 'res_id' in vals and 'partner_id' in vals:
                        existing = self.sudo().search([
                            ('res_model', '=', vals['res_model']),
                            ('res_id', '=', vals['res_id']),
                            ('partner_id', '=', vals['partner_id'])
                        ], limit=1)

                        if existing:
                            existing_followers |= existing

                return existing_followers if existing_followers else self.browse()
            else:
                raise