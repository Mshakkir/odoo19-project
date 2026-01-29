from odoo import models, fields


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _get_sequence(self):
        """Override to return bank-specific sequence"""
        self.ensure_one()

        journal = self.journal_id
        if not journal:
            return super()._get_sequence()

        journal_name = journal.name.upper()
        journal_code = journal.code.upper()

        # Detect bank
        is_snb = 'SNB' in journal_name or 'SNB' in journal_code or 'PSNB' in journal_code
        is_rajhi = 'RAJHI' in journal_name or 'RAJHI' in journal_code or 'PRAJHI' in journal_code

        # Get appropriate sequence code
        if self.payment_type == 'inbound':
            if is_snb:
                code = 'account.payment.customer.snb'
            elif is_rajhi:
                code = 'account.payment.customer.rajhi'
            else:
                return super()._get_sequence()
        elif self.payment_type == 'outbound':
            if is_snb:
                code = 'account.payment.supplier.snb'
            elif is_rajhi:
                code = 'account.payment.supplier.rajhi'
            else:
                return super()._get_sequence()
        else:
            return super()._get_sequence()

        # Return the custom sequence
        sequence = self.env['ir.sequence'].sudo().search([
            ('code', '=', code),
            '|',
            ('company_id', '=', self.company_id.id),
            ('company_id', '=', False)
        ], limit=1)

        return sequence if sequence else super()._get_sequence()