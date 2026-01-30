from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.depends('journal_id', 'payment_type', 'state')
    def _compute_name(self):
        """Override name computation to use bank-specific sequences"""
        for payment in self:
            # Skip if already has a valid name (not '/' and not empty)
            if payment.name and payment.name != '/' and payment.name != 'Draft':
                continue

            # Only assign sequence for payments that need it
            if not payment.journal_id or not payment.payment_type:
                payment.name = '/'
                continue

            journal_code = payment.journal_id.code.upper() if payment.journal_id.code else ''

            # Determine sequence code
            sequence_code = None
            if payment.payment_type == 'inbound':
                if journal_code == 'SNB':
                    sequence_code = 'account.payment.customer.snb'
                elif journal_code == 'RAJHI':
                    sequence_code = 'account.payment.customer.rajhi'
            elif payment.payment_type == 'outbound':
                if journal_code == 'SNB':
                    sequence_code = 'account.payment.supplier.snb'
                elif journal_code == 'RAJHI':
                    sequence_code = 'account.payment.supplier.rajhi'

            if sequence_code:
                sequence = self.env['ir.sequence'].sudo().search([
                    ('code', '=', sequence_code),
                    '|',
                    ('company_id', '=', payment.company_id.id),
                    ('company_id', '=', False)
                ], limit=1)

                if sequence:
                    # Only get new number if we don't have one yet
                    if not payment.name or payment.name == '/' or payment.name == 'Draft':
                        payment.name = sequence.next_by_id()
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
#             if payment.name and payment.name != '/':
#                 continue
#
#             journal = payment.journal_id
#             if not journal:
#                 payment.name = '/'
#                 continue
#
#             journal_code = journal.code.upper() if journal.code else ''
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
#                     _logger.info(f"✅ Using custom sequence {sequence_code} for journal {journal_code}")
#                     payment.name = sequence._next()
#                     continue
#                 else:
#                     _logger.warning(f"⚠️ Sequence {sequence_code} not found")
#
#             # Fallback to default
#             payment.name = '/'
#
#     name = fields.Char(
#         compute='_compute_name',
#         store=True,
#         readonly=False,
#         copy=False,
#         index='trigram',
#     )