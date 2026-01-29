from odoo import models, fields, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _get_sequence(self):
        """Override to use bank-specific sequences"""
        self.ensure_one()

        # Get the journal (bank account)
        journal = self.journal_id

        # Determine sequence based on payment type and bank
        if self.payment_type == 'inbound':  # Customer Payment
            # Check which bank journal is used
            if 'SNB' in journal.name.upper() or 'SNB' in journal.code.upper():
                sequence_code = 'account.payment.customer.snb'
            elif 'RAJHI' in journal.name.upper() or 'RAJHI' in journal.code.upper():
                sequence_code = 'account.payment.customer.rajhi'
            else:
                sequence_code = 'account.payment.customer'

        elif self.payment_type == 'outbound':  # Vendor Payment
            # Check which bank journal is used
            if 'SNB' in journal.name.upper() or 'SNB' in journal.code.upper():
                sequence_code = 'account.payment.supplier.snb'
            elif 'RAJHI' in journal.name.upper() or 'RAJHI' in journal.code.upper():
                sequence_code = 'account.payment.supplier.rajhi'
            else:
                sequence_code = 'account.payment.supplier'
        else:
            return super()._get_sequence()

        # Get or create the sequence
        return self.env['ir.sequence'].sudo().search([
            ('code', '=', sequence_code),
            ('company_id', 'in', [self.company_id.id, False])
        ], limit=1)

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set custom sequence number"""
        payments = super().create(vals_list)

        for payment in payments:
            if payment.name and payment.name != '/':
                continue

            sequence = payment._get_sequence()
            if sequence:
                payment.name = sequence._next()

        return payments


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    payment_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Payment Sequence',
        help='Specific sequence for this bank journal'
    )