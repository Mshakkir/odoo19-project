from odoo import models, api, _
import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.model
    def create(self, vals):
        """Override create to ensure partner context is passed"""
        # Ensure partner_id is in context for move creation
        if vals.get('partner_id') and 'default_partner_id' not in self.env.context:
            self = self.with_context(default_partner_id=vals['partner_id'])

        payment = super(AccountPayment, self).create(vals)

        _logger.info(
            f"Created payment {payment.name} for partner {payment.partner_id.name if payment.partner_id else 'N/A'}")

        return payment

    def _synchronize_to_moves(self, changed_fields):
        """Override to ensure partner is properly set on journal entry"""
        res = super()._synchronize_to_moves(changed_fields)

        # After synchronization, ensure partner is set on the move (if in draft state)
        for payment in self:
            if payment.move_id and payment.partner_id:
                # Only update if move is still in draft
                if payment.move_id.state == 'draft' and not payment.move_id.partner_id:
                    try:
                        payment.move_id.write({'partner_id': payment.partner_id.id})
                        _logger.info(f"Set partner {payment.partner_id.name} on draft move {payment.move_id.name}")
                    except Exception as e:
                        _logger.warning(f"Could not set partner on move {payment.move_id.name}: {str(e)}")

                # Ensure all move lines have partner set
                for line in payment.move_id.line_ids:
                    if not line.partner_id and line.account_id.account_type in ('asset_receivable', 'liability_payable',
                                                                                'asset_cash', 'liability_credit_card'):
                        try:
                            line.write({'partner_id': payment.partner_id.id})
                            _logger.info(f"Set partner on move line for account {line.account_id.code}")
                        except Exception as e:
                            _logger.warning(f"Could not set partner on line: {str(e)}")

        return res