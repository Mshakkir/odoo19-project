from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _set_payment_sequence(self):
        """Set bank-specific sequence for payment"""
        self.ensure_one()

        # Skip if already has a valid sequence number
        if self.name and self.name != '/':
            return

        journal = self.journal_id
        if not journal:
            return

        journal_code = journal.code.upper() if journal.code else ''

        _logger.info(
            f"🔍 Setting sequence for payment - Journal: {journal.name}, Code: {journal_code}, Type: {self.payment_type}")

        # Determine sequence code
        sequence_code = None
        if self.payment_type == 'inbound':
            if journal_code == 'SNB':
                sequence_code = 'account.payment.customer.snb'
            elif journal_code == 'RAJHI':
                sequence_code = 'account.payment.customer.rajhi'
        elif self.payment_type == 'outbound':
            if journal_code == 'SNB':
                sequence_code = 'account.payment.supplier.snb'
            elif journal_code == 'RAJHI':
                sequence_code = 'account.payment.supplier.rajhi'

        if not sequence_code:
            _logger.info(f"ℹ️ No custom sequence defined for journal {journal_code}")
            return

        # Get the sequence
        sequence = self.env['ir.sequence'].sudo().search([
            ('code', '=', sequence_code),
            '|',
            ('company_id', '=', self.company_id.id),
            ('company_id', '=', False)
        ], limit=1)

        if sequence:
            new_name = sequence._next()
            _logger.info(f"✅ Setting custom sequence: {sequence_code} -> {new_name}")
            self.name = new_name
        else:
            _logger.warning(f"⚠️ Sequence {sequence_code} not found in database")

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set custom sequence"""
        payments = super().create(vals_list)

        for payment in payments:
            payment._set_payment_sequence()

        return payments

    def write(self, vals):
        """Override write to handle sequence on state changes"""
        result = super().write(vals)

        # If name is being cleared or state is changing, reapply sequence
        if 'name' in vals or 'state' in vals:
            for payment in self:
                if not payment.name or payment.name == '/':
                    payment._set_payment_sequence()

        return result