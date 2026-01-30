from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to assign sequence only once"""

        for vals in vals_list:
            # Only if no name is provided
            if not vals.get('name') or vals.get('name') == '/':
                journal_id = vals.get('journal_id')
                payment_type = vals.get('payment_type')

                if journal_id and payment_type:
                    journal = self.env['account.journal'].browse(journal_id)
                    journal_code = journal.code.upper() if journal.code else ''

                    sequence_code = None
                    if payment_type == 'inbound':
                        if journal_code == 'SNB':
                            sequence_code = 'account.payment.customer.snb'
                        elif journal_code == 'RAJHI':
                            sequence_code = 'account.payment.customer.rajhi'
                    elif payment_type == 'outbound':
                        if journal_code == 'SNB':
                            sequence_code = 'account.payment.supplier.snb'
                        elif journal_code == 'RAJHI':
                            sequence_code = 'account.payment.supplier.rajhi'

                    if sequence_code:
                        sequence = self.env['ir.sequence'].sudo().search([
                            ('code', '=', sequence_code)
                        ], limit=1)

                        if sequence:
                            vals['name'] = sequence.next_by_id()
                            _logger.info(f"✅ CREATE: Assigned {vals['name']} from {sequence_code}")

        return super().create(vals_list)








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