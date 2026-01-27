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

    def _get_sequence(self):
        """Override to use custom sequences"""
        self.ensure_one()

        journal = self.journal_id

        # For inbound payments
        if self.payment_type == 'inbound' and journal.inbound_payment_sequence_id:
            return journal.inbound_payment_sequence_id

        # For outbound payments
        if self.payment_type == 'outbound' and journal.outbound_payment_sequence_id:
            return journal.outbound_payment_sequence_id

        # Default behavior
        return super(AccountPayment, self)._get_sequence()