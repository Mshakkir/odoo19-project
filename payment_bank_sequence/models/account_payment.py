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








# from odoo import models, api, fields
# import logging
#
# _logger = logging.getLogger(__name__)
#
#
# class AccountPayment(models.Model):
#     _inherit = 'account.payment'
#
#     @api.depends('journal_id', 'payment_type')
#     def _compute_name(self):
#         """Override name computation to use bank-specific sequences"""
#         for payment in self:
#             # Skip if not a real database record (no integer ID)
#             if not payment.id or not isinstance(payment.id, int):
#                 payment.name = '/'
#                 continue
#
#             # Skip if already has a valid name
#             if payment.name and payment.name != '/' and payment.name != 'Draft':
#                 continue
#
#             # Only assign sequence for saved payments
#             if not payment.journal_id or not payment.payment_type:
#                 payment.name = '/'
#                 continue
#
#             journal_code = payment.journal_id.code.upper() if payment.journal_id.code else ''
#
#             # Determine sequence code
#             sequence_code = None
#             if payment.payment_type == 'inbound':
#                 if journal_code == 'SNB':
#                     sequence_code = 'account.payment.customer.snb'
#                 elif journal_code == 'RAJHI':
#                     sequence_code = 'account.payment.customer.rajhi'
#             elif payment.payment_type == 'outbound':
#                 if journal_code == 'SNB':
#                     sequence_code = 'account.payment.supplier.snb'
#                 elif journal_code == 'RAJHI':
#                     sequence_code = 'account.payment.supplier.rajhi'
#
#             if sequence_code:
#                 sequence = self.env['ir.sequence'].sudo().search([
#                     ('code', '=', sequence_code),
#                     '|',
#                     ('company_id', '=', payment.company_id.id),
#                     ('company_id', '=', False)
#                 ], limit=1)
#
#                 if sequence:
#                     payment.name = sequence.next_by_id()
#                     _logger.info(f"✅ Assigned {sequence_code}: {payment.name} for payment ID {payment.id}")
#                     continue
#
#             # Fallback
#             payment.name = '/'
#
#     name = fields.Char(
#         compute='_compute_name',
#         store=True,
#         readonly=False,
#         copy=False,
#         index='trigram',
#     )
