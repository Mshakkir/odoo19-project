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

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to assign sequence before payment is created"""
        for vals in vals_list:
            if 'journal_id' in vals and 'payment_type' in vals:
                journal = self.env['account.journal'].browse(vals['journal_id'])
                payment_type = vals['payment_type']

                # Assign custom sequence for inbound payments
                if payment_type == 'inbound' and journal.inbound_payment_sequence_id:
                    vals['name'] = journal.inbound_payment_sequence_id.next_by_id()

                # Assign custom sequence for outbound payments
                elif payment_type == 'outbound' and journal.outbound_payment_sequence_id:
                    vals['name'] = journal.outbound_payment_sequence_id.next_by_id()

        return super().create(vals_list)

    def action_post(self):
        """Ensure sequence is set before posting"""
        for payment in self:
            if not payment.name or payment.name == '/':
                journal = payment.journal_id

                if payment.payment_type == 'inbound' and journal.inbound_payment_sequence_id:
                    payment.name = journal.inbound_payment_sequence_id.next_by_id()
                elif payment.payment_type == 'outbound' and journal.outbound_payment_sequence_id:
                    payment.name = journal.outbound_payment_sequence_id.next_by_id()

        return super().action_post()