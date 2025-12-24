# -*- coding: utf-8 -*-

from odoo import models
from psycopg2 import IntegrityError


class MailFollowers(models.Model):
    _inherit = 'mail.followers'

    def create(self, vals_list):
        """Prevent duplicate follower error in POS orders"""
        try:
            return super(MailFollowers, self).create(vals_list)
        except IntegrityError as e:
            if 'mail_followers_res_partner_res_model_id_uniq' in str(e):
                # Silently ignore duplicate follower attempts
                # Return existing follower instead
                if isinstance(vals_list, dict):
                    vals_list = [vals_list]

                existing_followers = self.env['mail.followers']
                for vals in vals_list:
                    existing = self.search([
                        ('res_model', '=', vals.get('res_model')),
                        ('res_id', '=', vals.get('res_id')),
                        ('partner_id', '=', vals.get('partner_id'))
                    ], limit=1)
                    if existing:
                        existing_followers |= existing

                return existing_followers
            else:
                raise