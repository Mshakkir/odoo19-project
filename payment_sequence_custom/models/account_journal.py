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
        payments = super().create(vals_list)

        for payment in payments:
            # Only process draft payments that need a sequence
            if payment.state == 'draft':
                journal = payment.journal_id

                # Check if we should use custom sequence
                should_update = False
                new_name = False

                # Assign custom sequence for inbound payments
                if payment.payment_type == 'inbound' and journal.inbound_payment_sequence_id:
                    new_name = journal.inbound_payment_sequence_id.next_by_id()
                    should_update = True

                # Assign custom sequence for outbound payments
                elif payment.payment_type == 'outbound' and journal.outbound_payment_sequence_id:
                    new_name = journal.outbound_payment_sequence_id.next_by_id()
                    should_update = True

                # Update the name if we have a custom sequence
                if should_update and new_name:
                    payment.write({'name': new_name})

        return payments

    def action_post(self):
        """Ensure custom sequence is set before posting"""
        for payment in self:
            # Only update if payment is in draft state
            if payment.state == 'draft':
                journal = payment.journal_id

                # Check if we need to update the sequence
                should_update = False
                new_name = False

                # Assign custom sequence for inbound payments
                if payment.payment_type == 'inbound' and journal.inbound_payment_sequence_id:
                    new_name = journal.inbound_payment_sequence_id.next_by_id()
                    should_update = True

                # Assign custom sequence for outbound payments
                elif payment.payment_type == 'outbound' and journal.outbound_payment_sequence_id:
                    new_name = journal.outbound_payment_sequence_id.next_by_id()
                    should_update = True

                # Update the name if we have a custom sequence
                if should_update and new_name:
                    # Use sudo to bypass readonly restriction
                    payment.sudo().write({'name': new_name})

        return super().action_post()

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        """Override to ensure the payment name is set before move creation"""
        # This method is called before creating the journal entry
        # Make sure we have the custom sequence set
        if self.state == 'draft':
            journal = self.journal_id

            # Assign custom sequence for inbound payments
            if self.payment_type == 'inbound' and journal.inbound_payment_sequence_id:
                if not self.name or self.name == '/' or self.name.startswith('DRAFT'):
                    new_name = journal.inbound_payment_sequence_id.next_by_id()
                    self.sudo().write({'name': new_name})

            # Assign custom sequence for outbound payments
            elif self.payment_type == 'outbound' and journal.outbound_payment_sequence_id:
                if not self.name or self.name == '/' or self.name.startswith('DRAFT'):
                    new_name = journal.outbound_payment_sequence_id.next_by_id()
                    self.sudo().write({'name': new_name})

        return super()._prepare_move_line_default_vals(write_off_line_vals)