# -*- coding: utf-8 -*-

from odoo import models, api
from psycopg2 import IntegrityError
import logging

_logger = logging.getLogger(__name__)


class MailFollowers(models.Model):
    _inherit = 'mail.followers'

    @api.model
    def _insert_followers(self, res_model, res_ids, partner_data,
                          customer_ids=None, check_existing=True,
                          existing_policy='skip', **kwargs):
        """
        Override to catch and handle duplicate follower insertion errors.
        This prevents the 'duplicate key value violates unique constraint' error
        when trying to add followers that already exist.

        Added **kwargs to handle any additional parameters like 'subtypes'
        that may be passed by different Odoo versions or modules.
        """
        try:
            return super(MailFollowers, self)._insert_followers(
                res_model=res_model,
                res_ids=res_ids,
                partner_data=partner_data,
                customer_ids=customer_ids,
                check_existing=check_existing,
                existing_policy=existing_policy,
                **kwargs  # Pass through any additional parameters
            )
        except IntegrityError as e:
            error_message = str(e)
            if 'mail_followers_unique_idx' in error_message or \
                    'duplicate key' in error_message or \
                    'mail_followers_res_partner_res_model_id_uniq' in error_message:
                _logger.warning(
                    'Duplicate follower detected for model %s, IDs %s. '
                    'Ignoring duplicate insertion. Error: %s',
                    res_model, res_ids, error_message
                )
                # Rollback the failed transaction
                self.env.cr.rollback()
                # Return empty recordset
                return self.browse()
            else:
                # Re-raise if it's a different IntegrityError
                _logger.error('Non-duplicate IntegrityError: %s', error_message)
                raise
        except TypeError as e:
            # Handle parameter mismatch errors gracefully
            _logger.error('TypeError in _insert_followers: %s. Args: %s', e, kwargs)
            raise