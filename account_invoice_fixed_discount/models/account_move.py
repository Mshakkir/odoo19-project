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

    @api.depends('invoice_line_ids.price_subtotal', 'global_discount_fixed')
    def _compute_amounts_with_discount(self):
        """Calculate amounts before and after global discount for display."""
        for move in self:
            if move.is_invoice():
                # Calculate ORIGINAL amount WITHOUT any discounts
                amount_undiscounted = sum(
                    line.quantity * line.price_unit
                    for line in move.invoice_line_ids
                    if not line.display_type
                )
                move.amount_undiscounted = amount_undiscounted
                move.amount_after_discount = amount_undiscounted - (move.global_discount_fixed or 0.0)

                _logger.info(
                    f"Invoice {move.name} - Original: {amount_undiscounted}, "
                    f"Discount: {move.global_discount_fixed}, After: {move.amount_after_discount}"
                )
            else:
                move.amount_undiscounted = 0.0
                move.amount_after_discount = 0.0

    @api.depends(
        'invoice_line_ids.price_subtotal',
        'invoice_line_ids.price_total',
        'global_discount_fixed',
    )
    def _compute_amount(self):
        """
        Extend account.move amount compute to consider global_discount_fixed.
        First call super() to let Odoo compute its normal totals.
        Then apply the fixed global discount on the invoice.
        """
        # Let core compute amounts first
        super(AccountMove, self)._compute_amount()

        for move in self:
            # Apply only to invoices / vendor bills / refunds
            if move.move_type not in ('out_invoice', 'in_invoice', 'out_refund', 'in_refund'):
                continue

            # Only real invoice lines, ignore section/note lines
            invoice_lines = move.invoice_line_ids.filtered(lambda l: not l.display_type)

            # 🔥 CRITICAL FIX: Skip if no lines exist yet
            if not invoice_lines:
                _logger.warning(f"Skipping discount calculation for {move.name or 'New'} - no invoice lines yet")
                continue

            amount_untaxed = sum(invoice_lines.mapped('price_subtotal'))
            amount_tax = sum(invoice_lines.mapped('price_total')) - amount_untaxed

            # 🔥 CRITICAL FIX: Skip if amounts are still zero (lines not ready)
            if amount_untaxed == 0 and move.global_discount_fixed > 0:
                _logger.warning(
                    f"Skipping discount for {move.name or 'New'} - "
                    f"lines exist but amounts are zero (lines={len(invoice_lines)})"
                )
                continue

            # Use currency rounder
            round_func = getattr(move.currency_id, 'round', lambda x: round(x, 2))

            # If discount exists, apply discount logic
            if move.global_discount_fixed and move.global_discount_fixed > 0:
                # New untaxed after discount
                amount_untaxed_after = amount_untaxed - move.global_discount_fixed
                if amount_untaxed_after < 0:
                    amount_untaxed_after = 0.0

                # Tax must also be reduced proportionally
                if amount_untaxed > 0:
                    discount_ratio = amount_untaxed_after / amount_untaxed
                    amount_tax_after = amount_tax * discount_ratio
                else:
                    amount_tax_after = 0.0

                amount_total_after = amount_untaxed_after + amount_tax_after

                # Save values
                move.amount_untaxed = round_func(amount_untaxed_after)
                move.amount_tax = round_func(amount_tax_after)
                move.amount_total = round_func(amount_total_after)

                _logger.info(
                    f"✅ Applied discount to {move.name or 'New'}: "
                    f"Original={amount_untaxed}, Discount={move.global_discount_fixed}, "
                    f"After={amount_untaxed_after}, Tax={amount_tax_after}, Total={amount_total_after}"
                )
            else:
                # No discount → keep original values (reassign for safety)
                move.amount_untaxed = round_func(amount_untaxed)
                move.amount_tax = round_func(amount_tax)
                move.amount_total = round_func(amount_untaxed + amount_tax)

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to ensure discount is recomputed after lines are created."""
        moves = super(AccountMove, self).create(vals_list)

        # Recompute amounts for invoices with global discount
        for move in moves:
            if move.is_invoice() and move.global_discount_fixed and move.global_discount_fixed > 0:
                _logger.info(f"🔄 Recomputing amounts after create for {move.name}")
                # Force recomputation now that lines exist
                move._compute_amount()

        return moves

    def write(self, vals):
        """Override write to recompute when discount or lines change."""
        res = super(AccountMove, self).write(vals)

        # If discount changed or lines changed, recompute
        if 'global_discount_fixed' in vals or 'invoice_line_ids' in vals:
            for move in self:
                if move.is_invoice() and move.state == 'draft':
                    _logger.info(f"🔄 Recomputing amounts after write for {move.name}")
                    move._compute_amount()

        return res