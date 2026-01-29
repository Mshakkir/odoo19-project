from odoo import models, api, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _get_bank_specific_sequence(self):
        """Get bank-specific sequence based on journal"""
        self.ensure_one()

        journal = self.journal_id
        if not journal:
            return None

        journal_name = journal.name.upper()
        journal_code = journal.code.upper()

        # Detect bank type
        is_snb = 'SNB' in journal_name or 'SNB' in journal_code
        is_rajhi = 'RAJHI' in journal_name or 'RAJHI' in journal_code

        # Determine sequence code
        sequence_code = None
        if self.payment_type == 'inbound':  # Customer Payment
            if is_snb:
                sequence_code = 'account.payment.customer.snb'
            elif is_rajhi:
                sequence_code = 'account.payment.customer.rajhi'
        elif self.payment_type == 'outbound':  # Vendor Payment
            if is_snb:
                sequence_code = 'account.payment.supplier.snb'
            elif is_rajhi:
                sequence_code = 'account.payment.supplier.rajhi'

        if not sequence_code:
            return None

        # Find sequence
        sequence = self.env['ir.sequence'].sudo().search([
            ('code', '=', sequence_code),
            '|',
            ('company_id', '=', self.company_id.id),
            ('company_id', '=', False)
        ], limit=1)

        return sequence

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set bank-specific sequence number"""

        # First, create records without triggering default sequence
        for vals in vals_list:
            # If no name is set or it's '/', we'll set our custom sequence
            if not vals.get('name') or vals.get('name') == '/':
                vals['name'] = '/'  # Temporarily set to avoid default sequence

        # Create the payments
        payments = super().create(vals_list)

        # Now apply custom sequences
        for payment in payments:
            if payment.name == '/' or not payment.name:
                sequence = payment._get_bank_specific_sequence()

                if sequence:
                    # Use our custom sequence
                    new_name = sequence._next()
                    payment.sudo().write({'name': new_name})
                # If no custom sequence found, let default sequence apply
                elif payment.name == '/':
                    # Get default sequence
                    if payment.payment_type == 'inbound':
                        seq_code = 'account.payment.customer'
                    elif payment.payment_type == 'outbound':
                        seq_code = 'account.payment.supplier'
                    else:
                        seq_code = 'account.payment.transfer'

                    default_seq = self.env['ir.sequence'].search([
                        ('code', '=', seq_code)
                    ], limit=1)

                    if default_seq:
                        payment.sudo().write({'name': default_seq._next()})

        return payments

    def write(self, vals):
        """Override write to handle sequence on state change"""
        result = super().write(vals)

        # If state is being set and name is still '/', apply sequence
        if vals.get('state') and not vals.get('name'):
            for payment in self:
                if payment.name == '/' or not payment.name:
                    sequence = payment._get_bank_specific_sequence()
                    if sequence:
                        payment.sudo().write({'name': sequence._next()})

        return result