from odoo import models, api, _
import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to ensure partner context is passed"""
        # vals_list is a list of dictionaries in Odoo 13+
        # Check if we need to add partner context
        if vals_list and isinstance(vals_list, list) and len(vals_list) > 0:
            first_vals = vals_list[0]
            if first_vals.get('partner_id') and 'default_partner_id' not in self.env.context:
                self = self.with_context(default_partner_id=first_vals['partner_id'])

        payments = super(AccountPayment, self).create(vals_list)

        for payment in payments:
            _logger.info(
                f"Created payment {payment.name} for partner {payment.partner_id.name if payment.partner_id else 'N/A'}")

        return payments

    def _synchronize_to_moves(self, changed_fields):
        """Override to ensure partner is properly set on journal entry"""
        res = super()._synchronize_to_moves(changed_fields)

        # After synchronization, ensure partner is set on the move and all lines
        for payment in self:
            if payment.move_id and payment.partner_id:
                # Set partner on move if not set
                if not payment.move_id.partner_id:
                    try:
                        payment.move_id.write({'partner_id': payment.partner_id.id})
                        _logger.info(f"Set partner {payment.partner_id.name} on move {payment.move_id.name}")
                    except Exception as e:
                        _logger.warning(f"Could not set partner on move {payment.move_id.name}: {str(e)}")

                # CRITICAL: Ensure all move lines have partner set
                # This is essential for Partner Ledger to show the payment
                for line in payment.move_id.line_ids:
                    if not line.partner_id:
                        try:
                            line.write({'partner_id': payment.partner_id.id})
                            _logger.info(
                                f"Set partner {payment.partner_id.name} on move line for account {line.account_id.code}")
                        except Exception as e:
                            _logger.warning(f"Could not set partner on line: {str(e)}")

        return res

    def action_post(self):
        """Override action_post to ensure partner is set on journal entry lines after posting"""
        res = super().action_post()

        # After posting, double-check that partner is set on all lines
        for payment in self:
            if payment.move_id and payment.partner_id:
                lines_without_partner = payment.move_id.line_ids.filtered(lambda l: not l.partner_id)

                if lines_without_partner:
                    _logger.warning(
                        f"Found {len(lines_without_partner)} lines without partner after posting payment {payment.name}")

                    # Force set partner on these lines
                    for line in lines_without_partner:
                        try:
                            # Use sudo() to bypass any access rights issues
                            line.sudo().write({'partner_id': payment.partner_id.id})
                            _logger.info(
                                f"POST-FIX: Set partner {payment.partner_id.name} on line {line.id} for account {line.account_id.code}")
                        except Exception as e:
                            _logger.error(f"CRITICAL: Could not set partner on line {line.id}: {str(e)}")

                # Log final status
                for line in payment.move_id.line_ids:
                    _logger.info(
                        f"Final line status - Account: {line.account_id.code}, Partner: {line.partner_id.name if line.partner_id else 'MISSING'}, Debit: {line.debit}, Credit: {line.credit}")

        return res