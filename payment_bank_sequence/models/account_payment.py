from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.depends('journal_id', 'payment_type')
    def _compute_name(self):
        """Override name computation to use bank-specific sequences"""
        for payment in self:
            # Skip if not a real database record
            if not payment.id or not isinstance(payment.id, int):
                payment.name = '/'
                continue

            # Skip if already has a valid name
            if payment.name and payment.name != '/' and payment.name != 'Draft':
                continue

            # Only assign sequence for saved payments
            if not payment.journal_id or not payment.payment_type:
                payment.name = '/'
                continue

            journal_code = payment.journal_id.code.upper() if payment.journal_id.code else ''

            # Determine which sequence to use (shared between banks)
            sequence_code = None
            bank_prefix = ''

            if payment.payment_type == 'inbound':
                sequence_code = 'account.payment.customer.shared'
                # Set bank prefix based on journal
                if journal_code == 'SNB':
                    bank_prefix = 'PREC/SNB/'
                elif journal_code == 'RAJHI':
                    bank_prefix = 'PREC/RAJHI/'
                else:
                    bank_prefix = 'PREC/'

            elif payment.payment_type == 'outbound':
                sequence_code = 'account.payment.supplier.shared'
                # Set bank prefix based on journal
                if journal_code == 'SNB':
                    bank_prefix = 'PAY/SNB/'
                elif journal_code == 'RAJHI':
                    bank_prefix = 'PAY/RAJHI/'
                else:
                    bank_prefix = 'PAY/'

            if sequence_code:
                sequence = self.env['ir.sequence'].sudo().search([
                    ('code', '=', sequence_code),
                    '|',
                    ('company_id', '=', payment.company_id.id),
                    ('company_id', '=', False)
                ], limit=1)

                if sequence:
                    # Get next number from sequence
                    seq_number = sequence.next_by_id()
                    # Extract just the number part (remove any existing prefix)
                    number_only = seq_number.split('/')[-1]
                    # Combine bank prefix with year and number
                    year = fields.Date.today().strftime('%Y')
                    payment.name = f"{bank_prefix}{year}/{number_only}"
                    _logger.info(f"✅ Assigned {sequence_code}: {payment.name} for payment ID {payment.id}")
                    continue

            # Fallback
            payment.name = '/'

    name = fields.Char(
        compute='_compute_name',
        store=True,
        readonly=False,
        copy=False,
        index='trigram',
    )

    def _synchronize_to_moves(self, changed_fields):
        """Override to sync payment name to journal entry"""
        res = super(AccountPayment, self)._synchronize_to_moves(changed_fields)

        # Sync the name field to the move
        if self.move_id and self.name and self.name != '/':
            try:
                # Use sudo to bypass access rights and write directly
                self.move_id.sudo().write({'name': self.name})
                _logger.info(f"✅ Synced move name to: {self.name}")
            except Exception as e:
                _logger.warning(f"Could not sync move name: {e}")

        return res


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_sequence(self):
        """Override to prevent auto-sequencing for payment moves"""
        self.ensure_one()

        # Check if this move is linked to a payment
        # Use search instead of direct field access
        payment = self.env['account.payment'].search([('move_id', '=', self.id)], limit=1)

        if payment:
            # Return empty sequence to prevent auto-sequencing
            # The payment name will be synced instead
            return self.env['ir.sequence']

        # For non-payment moves, use standard sequence logic
        return super(AccountMove, self)._get_sequence()

    def _post(self, soft=True):
        """Override _post to sync payment name after posting"""
        res = super(AccountMove, self)._post(soft=soft)

        for move in self:
            # Check if this move is linked to a payment
            payment = self.env['account.payment'].search([('move_id', '=', move.id)], limit=1)

            if payment and payment.name and payment.name != '/':
                try:
                    # Sync the move name with payment name
                    move.sudo().write({'name': payment.name})
                    _logger.info(f"✅ Posted move {move.id} with name: {payment.name}")
                except Exception as e:
                    _logger.warning(f"Could not sync move name after post: {e}")

        return res

