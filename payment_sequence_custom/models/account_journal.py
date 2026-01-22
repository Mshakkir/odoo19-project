from odoo import fields, models, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    inbound_payment_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Inbound Payment Sequence',
        help='Sequence for customer payments (incoming)',
        copy=False
    )

    outbound_payment_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Outbound Payment Sequence',
        help='Sequence for vendor payments (outgoing)',
        copy=False
    )


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.model
    def _get_sequence(self):
        """Override to use custom sequences based on payment type"""
        # Get the payment from the context or use self
        payment = self if self else self.env['account.payment']

        if hasattr(payment, 'payment_type') and hasattr(payment, 'journal_id'):
            journal = payment.journal_id

            if payment.payment_type == 'inbound' and journal.inbound_payment_sequence_id:
                return journal.inbound_payment_sequence_id
            elif payment.payment_type == 'outbound' and journal.outbound_payment_sequence_id:
                return journal.outbound_payment_sequence_id

        return super()._get_sequence()

    def _post(self):
        """Override _post to assign sequence from custom sequences"""
        for payment in self:
            if not payment.name or payment.name == '/':
                journal = payment.journal_id

                if payment.payment_type == 'inbound' and journal.inbound_payment_sequence_id:
                    payment.name = journal.inbound_payment_sequence_id.next_by_id()
                elif payment.payment_type == 'outbound' and journal.outbound_payment_sequence_id:
                    payment.name = journal.outbound_payment_sequence_id.next_by_id()

        return super()._post()