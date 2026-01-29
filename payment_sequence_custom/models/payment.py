# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to assign different sequences based on payment type"""
        for vals in vals_list:
            # Check if name needs to be assigned
            if 'name' not in vals or not vals.get('name') or vals.get('name') in ('/', 'New'):
                # Get partner_type and journal information
                partner_type = vals.get('partner_type')
                payment_type = vals.get('payment_type')
                journal_id = vals.get('journal_id')

                # Determine which sequence to use based on partner_type
                # partner_type can be 'customer' or 'supplier'
                if partner_type == 'customer':
                    # Customer payment - Use PRSNB sequence
                    sequence_code = 'account.payment.customer'
                    sequence = self.env['ir.sequence'].next_by_code(sequence_code)
                    if sequence:
                        vals['name'] = sequence
                    else:
                        # Fallback to journal sequence if custom sequence not found
                        vals['name'] = self.env['ir.sequence'].next_by_code('account.payment') or '/'

                elif partner_type == 'supplier':
                    # Vendor/Supplier payment - Use PASNB or PSNB sequence
                    sequence_code = 'account.payment.supplier'
                    sequence = self.env['ir.sequence'].next_by_code(sequence_code)
                    if sequence:
                        vals['name'] = sequence
                    else:
                        # Fallback to journal sequence if custom sequence not found
                        vals['name'] = self.env['ir.sequence'].next_by_code('account.payment') or '/'

        return super(AccountPayment, self).create(vals_list)