# -*- coding: utf-8 -*-
from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    global_discount_fixed = fields.Monetary(
        string="Global Discount (Fixed)",
        default=0.0,
        currency_field="currency_id",
        tracking=True,
        readonly=False,
    )

    amount_undiscounted = fields.Monetary(
        string='Amount Undiscounted',
        compute='_compute_amounts_with_discount',
        store=True,
        currency_field='currency_id'
    )

    amount_after_discount = fields.Monetary(
        string='Amount After Discount',
        compute='_compute_amounts_with_discount',
        store=True,
        currency_field='currency_id'
    )

    @api.depends('invoice_line_ids.price_subtotal', 'invoice_line_ids.price_total', 'global_discount_fixed')
    def _compute_amounts_with_discount(self):
        """Calculate amounts before and after global discount for display."""
        for move in self:
            if move.is_invoice():
                amount_undiscounted = sum(
                    line.price_subtotal
                    for line in move.invoice_line_ids
                    if not line.display_type
                )
                move.amount_undiscounted = amount_undiscounted
                move.amount_after_discount = amount_undiscounted - (move.global_discount_fixed or 0.0)
            else:
                move.amount_undiscounted = 0.0
                move.amount_after_discount = 0.0

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.balance',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id',
        'global_discount_fixed',
    )
    def _compute_amount(self):
        """
        Override the main amount computation to apply global discount.
        This method is called by Odoo to compute invoice totals.
        """
        # First, let Odoo compute the standard amounts
        super(AccountMove, self)._compute_amount()

        # Now apply our global discount
        for move in self:
            # Only process invoices
            if not move.is_invoice():
                continue

            # Skip if no discount
            if not move.global_discount_fixed or move.global_discount_fixed <= 0:
                continue

            # Get invoice lines (product lines only)
            product_lines = move.invoice_line_ids.filtered(lambda l: not l.display_type)
            if not product_lines:
                _logger.warning(f"⚠️ No product lines in {move.name or 'New'}")
                continue

            # Calculate original amounts from lines
            original_subtotal = sum(product_lines.mapped('price_subtotal'))
            original_total_with_tax = sum(product_lines.mapped('price_total'))
            original_tax = original_total_with_tax - original_subtotal

            _logger.info(
                f"📊 {move.name or 'New'} - Original: Subtotal={original_subtotal}, "
                f"Tax={original_tax}, Total={original_total_with_tax}"
            )

            # Skip if subtotal is zero
            if original_subtotal <= 0:
                _logger.warning(f"⚠️ Subtotal is zero for {move.name or 'New'}")
                continue

            # Apply discount to subtotal
            new_subtotal = original_subtotal - move.global_discount_fixed
            if new_subtotal < 0:
                new_subtotal = 0.0

            # Proportionally adjust tax
            if original_subtotal > 0:
                discount_ratio = new_subtotal / original_subtotal
                new_tax = original_tax * discount_ratio
            else:
                new_tax = 0.0

            new_total = new_subtotal + new_tax

            # Round amounts
            currency = move.currency_id or move.company_id.currency_id
            new_subtotal = currency.round(new_subtotal)
            new_tax = currency.round(new_tax)
            new_total = currency.round(new_total)

            # Update move amounts WITHOUT triggering recursion
            # We use update() instead of assignment to avoid triggering compute
            move.update({
                'amount_untaxed': new_subtotal,
                'amount_tax': new_tax,
                'amount_total': new_total,
                'amount_residual': new_total,
            })

            _logger.warning(
                f"✅✅✅ DISCOUNT APPLIED to {move.name or 'New'}: "
                f"Discount={move.global_discount_fixed}, New Subtotal={new_subtotal}, "
                f"New Tax={new_tax}, New Total={new_total}"
            )

    @api.onchange('global_discount_fixed')
    def _onchange_global_discount_fixed(self):
        """Trigger recomputation when discount changes in the UI."""
        if self.is_invoice():
            _logger.info(f"🔄 Discount changed in UI for {self.name or 'New'}")
            # Trigger amount recomputation
            self._compute_amount()

    @api.model_create_multi
    def create(self, vals_list):
        """Ensure discount is applied after invoice creation."""
        _logger.info(f"📝 Creating {len(vals_list)} invoice(s)")

        # Create invoices normally
        moves = super(AccountMove, self).create(vals_list)

        # Apply discount to invoices that have it
        for move in moves:
            if move.is_invoice() and move.global_discount_fixed and move.global_discount_fixed > 0:
                _logger.info(f"🎯 Invoice created with discount: {move.global_discount_fixed}")
                # The _compute_amount will be automatically triggered by Odoo
                # But we force it here to ensure it runs
                move._compute_amount()

        return moves

    def write(self, vals):
        """Recompute when discount changes."""
        # Track if discount is changing
        discount_changing = 'global_discount_fixed' in vals

        # Perform the write
        res = super(AccountMove, self).write(vals)

        # Recompute if discount changed
        if discount_changing:
            for move in self.filtered(lambda m: m.is_invoice() and m.state == 'draft'):
                _logger.info(f"🔄 Discount changed for {move.name}, recomputing")
                move._compute_amount()

        return res