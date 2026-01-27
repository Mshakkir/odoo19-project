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
        """Override create to assign custom sequence"""
        # First call super to create the records
        payments = super().create(vals_list)

        # Then update the sequence for each payment
        for payment in payments:
            if payment.state == 'draft' and payment.name == '/':
                self._assign_custom_sequence(payment)

        return payments

    def _assign_custom_sequence(self, payment=None):
        """Assign custom sequence to payment based on type"""
        if payment is None:
            payment = self

        journal = payment.journal_id
        new_name = False

        # Assign custom sequence for inbound payments
        if payment.payment_type == 'inbound' and journal.inbound_payment_sequence_id:
            new_name = journal.inbound_payment_sequence_id.next_by_id()

        # Assign custom sequence for outbound payments
        elif payment.payment_type == 'outbound' and journal.outbound_payment_sequence_id:
            new_name = journal.outbound_payment_sequence_id.next_by_id()

        # Update the name if we have a custom sequence
        if new_name:
            # Use sudo to bypass readonly restrictions
            payment.sudo().write({'name': new_name})
            return True

        return False

    def action_post(self):
        """Ensure custom sequence is set before posting"""
        for payment in self:
            # Only update if payment is in draft state and has default sequence
            if payment.state == 'draft' and (not payment.name or payment.name == '/'):
                self._assign_custom_sequence(payment)

        return super().action_post()

    def write(self, vals):
        """Intercept write to set sequence before journal entry is created"""
        # If state is changing to something other than draft and name is still default
        if 'state' in vals and vals.get('state') != 'draft':
            for payment in self:
                if payment.state == 'draft' and (not payment.name or payment.name == '/'):
                    self._assign_custom_sequence(payment)

        return super().write(vals)