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

    def action_post(self):
        """Override action_post to assign sequence from custom sequences"""
        for payment in self:
            journal = payment.journal_id

            # Assign sequence before posting
            if payment.payment_type == 'inbound' and journal.inbound_payment_sequence_id:
                if not payment.name or payment.name == '/':
                    payment.name = journal.inbound_payment_sequence_id.next_by_id()
            elif payment.payment_type == 'outbound' and journal.outbound_payment_sequence_id:
                if not payment.name or payment.name == '/':
                    payment.name = journal.outbound_payment_sequence_id.next_by_id()

        return super().action_post()

    def _seek_for_lines(self):
        """Override to ensure sequence is applied"""
        for payment in self:
            journal = payment.journal_id

            if payment.payment_type == 'inbound' and journal.inbound_payment_sequence_id:
                if not payment.name or payment.name == '/':
                    payment.name = journal.inbound_payment_sequence_id.next_by_id()
            elif payment.payment_type == 'outbound' and journal.outbound_payment_sequence_id:
                if not payment.name or payment.name == '/':
                    payment.name = journal.outbound_payment_sequence_id.next_by_id()

        return super()._seek_for_lines()