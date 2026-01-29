from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _get_sequence(self):
        """Override to return bank-specific sequence based on journal code"""
        self.ensure_one()

        journal = self.journal_id
        if not journal:
            return super()._get_sequence()

        journal_code = journal.code.upper() if journal.code else ''

        _logger.info(
            f"🔍 Payment sequence check - Journal: {journal.name}, Code: {journal_code}, Type: {self.payment_type}")

        # Determine sequence code based on exact journal codes
        sequence_code = None

        if self.payment_type == 'inbound':  # Customer Payment
            if journal_code == 'SNB':
                sequence_code = 'account.payment.customer.snb'
            elif journal_code == 'RAJHI':
                sequence_code = 'account.payment.customer.rajhi'
        elif self.payment_type == 'outbound':  # Vendor Payment
            if journal_code == 'SNB':
                sequence_code = 'account.payment.supplier.snb'
            elif journal_code == 'RAJHI':
                sequence_code = 'account.payment.supplier.rajhi'

        if not sequence_code:
            _logger.info(f"❌ No custom sequence for journal {journal_code}, using default")
            return super()._get_sequence()

        # Find the custom sequence
        sequence = self.env['ir.sequence'].sudo().search([
            ('code', '=', sequence_code),
            '|',
            ('company_id', '=', self.company_id.id),
            ('company_id', '=', False)
        ], limit=1)

        if sequence:
            _logger.info(f"✅ Using custom sequence: {sequence_code} -> {sequence.name}")
            return sequence
        else:
            _logger.warning(f"⚠️ Custom sequence {sequence_code} not found, using default")
            return super()._get_sequence()