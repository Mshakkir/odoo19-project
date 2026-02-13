# from odoo import models, api, _
# import logging
#
# _logger = logging.getLogger(__name__)
#
#
# class AccountPayment(models.Model):
#     _inherit = 'account.payment'
#
#     @api.model_create_multi
#     def create(self, vals_list):
#         """Override create to ensure partner context is passed"""
#         # vals_list is a list of dictionaries in Odoo 13+
#         # Check if we need to add partner context
#         if vals_list and isinstance(vals_list, list) and len(vals_list) > 0:
#             first_vals = vals_list[0]
#             if first_vals.get('partner_id') and 'default_partner_id' not in self.env.context:
#                 self = self.with_context(default_partner_id=first_vals['partner_id'])
#
#         payments = super(AccountPayment, self).create(vals_list)
#
#         for payment in payments:
#             _logger.info(
#                 f"Created payment {payment.name} for partner {payment.partner_id.name if payment.partner_id else 'N/A'}")
#
#         return payments
#
#     def _synchronize_to_moves(self, changed_fields):
#         """Override to ensure partner is properly set on journal entry"""
#         res = super()._synchronize_to_moves(changed_fields)
#
#         # After synchronization, ensure partner is set on the move and all lines
#         for payment in self:
#             if payment.move_id and payment.partner_id:
#                 # Set partner on move if not set
#                 if not payment.move_id.partner_id:
#                     try:
#                         payment.move_id.write({'partner_id': payment.partner_id.id})
#                         _logger.info(f"Set partner {payment.partner_id.name} on move {payment.move_id.name}")
#                     except Exception as e:
#                         _logger.warning(f"Could not set partner on move {payment.move_id.name}: {str(e)}")
#
#                 # CRITICAL: Ensure all move lines have partner set
#                 # This is essential for Partner Ledger to show the payment
#                 for line in payment.move_id.line_ids:
#                     if not line.partner_id:
#                         try:
#                             line.write({'partner_id': payment.partner_id.id})
#                             _logger.info(
#                                 f"Set partner {payment.partner_id.name} on move line for account {line.account_id.code}")
#                         except Exception as e:
#                             _logger.warning(f"Could not set partner on line: {str(e)}")
#
#         return res
#
#     def action_post(self):
#         """Override action_post to ensure partner is set on journal entry lines after posting"""
#         res = super().action_post()
#
#         # After posting, double-check that partner is set on all lines
#         for payment in self:
#             if payment.move_id and payment.partner_id:
#                 lines_without_partner = payment.move_id.line_ids.filtered(lambda l: not l.partner_id)
#
#                 if lines_without_partner:
#                     _logger.warning(
#                         f"Found {len(lines_without_partner)} lines without partner after posting payment {payment.name}")
#
#                     # Force set partner on these lines
#                     for line in lines_without_partner:
#                         try:
#                             # Use sudo() to bypass any access rights issues
#                             line.sudo().write({'partner_id': payment.partner_id.id})
#                             _logger.info(
#                                 f"POST-FIX: Set partner {payment.partner_id.name} on line {line.id} for account {line.account_id.code}")
#                         except Exception as e:
#                             _logger.error(f"CRITICAL: Could not set partner on line {line.id}: {str(e)}")
#
#                 # Log final status
#                 for line in payment.move_id.line_ids:
#                     _logger.info(
#                         f"Final line status - Account: {line.account_id.code}, Partner: {line.partner_id.name if line.partner_id else 'MISSING'}, Debit: {line.debit}, Credit: {line.credit}")
#
#         return res

from odoo import models, api, fields, _
import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # Add relation to bill allocation history
    bill_allocation_history_ids = fields.One2many('payment.allocation.history', 'payment_id',
                                                  string='Bill Allocations', readonly=True)
    bill_allocation_count = fields.Integer(string='Bill Allocations', compute='_compute_bill_allocation_count')

    @api.depends('bill_allocation_history_ids')
    def _compute_bill_allocation_count(self):
        for rec in self:
            rec.bill_allocation_count = len(rec.bill_allocation_history_ids)

    def action_view_bill_allocation_history(self):
        """Open wizard to display bill allocation details"""
        self.ensure_one()

        if not self.bill_allocation_history_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Allocation History'),
                    'message': _(
                        'This payment does not have bill allocation history. This feature only works for payments created through the "Against Receipts" wizard.'),
                    'type': 'info',
                }
            }

        # Create wizard record
        wizard = self.env['bill.allocation.display.wizard'].create({
            'payment_id': self.id,
        })

        # Create wizard lines from allocation history
        for history in self.bill_allocation_history_ids:
            self.env['bill.allocation.display.line'].create({
                'wizard_id': wizard.id,
                'invoice_vendor_bill_id': history.invoice_vendor_bill_id.id,
                'bill_number': history.bill_number,
                'bill_date': history.bill_date,
                'amount_total': history.amount_total,
                'amount_due': history.amount_due,
                'amount_paid': history.amount_paid,
                'balance_after_payment': history.balance_after_payment,
            })

        return {
            'name': _('Bill Allocation Details'),
            'type': 'ir.actions.act_window',
            'res_model': 'bill.allocation.display.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }

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