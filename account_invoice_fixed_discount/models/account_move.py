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

                _logger.info(f"Compute discount amounts: {move.name or 'New'} - "
                             f"Undiscounted={amount_undiscounted}, Discount={move.global_discount_fixed}, "
                             f"After={move.amount_after_discount}")
            else:
                move.amount_undiscounted = 0.0
                move.amount_after_discount = 0.0

    def _recompute_tax_lines(self, recompute_tax_base_amount=False):
        """
        This is THE key method that Odoo uses to compute taxes.
        We override it to apply discount AFTER taxes are computed.
        """
        _logger.info(f"=== _recompute_tax_lines called for {self.mapped('name')} ===")

        # Let Odoo compute taxes normally
        res = super()._recompute_tax_lines(recompute_tax_base_amount=recompute_tax_base_amount)

        # Now apply our global discount
        for move in self:
            if not move.is_invoice():
                continue

            if not move.global_discount_fixed or move.global_discount_fixed <= 0:
                continue

            # Get product lines
            product_lines = move.invoice_line_ids.filtered(lambda l: not l.display_type)
            if not product_lines:
                _logger.warning(f"No product lines in {move.name or 'New'}")
                continue

            # Calculate totals from lines
            subtotal = sum(product_lines.mapped('price_subtotal'))
            total_with_tax = sum(product_lines.mapped('price_total'))
            tax_amount = total_with_tax - subtotal

            _logger.info(f"Before discount - Subtotal: {subtotal}, Tax: {tax_amount}, Total: {total_with_tax}")

            if subtotal <= 0:
                continue

            # Apply discount to subtotal
            new_subtotal = subtotal - move.global_discount_fixed
            if new_subtotal < 0:
                new_subtotal = 0.0

            # Proportionally reduce tax
            discount_ratio = new_subtotal / subtotal if subtotal > 0 else 0.0
            new_tax = tax_amount * discount_ratio
            new_total = new_subtotal + new_tax

            # Round using currency
            currency = move.currency_id or move.company_id.currency_id
            new_subtotal = currency.round(new_subtotal)
            new_tax = currency.round(new_tax)
            new_total = currency.round(new_total)

            # Update move totals
            move.amount_untaxed = new_subtotal
            move.amount_tax = new_tax
            move.amount_total = new_total
            move.amount_residual = new_total if move.state == 'posted' else new_total

            _logger.info(
                f"✅✅✅ DISCOUNT APPLIED to {move.name or 'New'}: "
                f"New Subtotal={new_subtotal}, New Tax={new_tax}, New Total={new_total}"
            )

        return res

    @api.onchange('global_discount_fixed')
    def _onchange_global_discount_fixed(self):
        """Trigger recomputation when discount changes in the UI."""
        if self.is_invoice():
            _logger.info(f"Discount changed in UI for {self.name or 'New'}, triggering recompute")
            self._recompute_tax_lines()

    @api.model_create_multi
    def create(self, vals_list):
        """Ensure discount is applied on create."""
        moves = super().create(vals_list)

        for move in moves:
            if move.is_invoice() and move.global_discount_fixed and move.global_discount_fixed > 0:
                _logger.info(f"New invoice created with discount: {move.global_discount_fixed}")
                # Force tax recomputation
                move._recompute_tax_lines()

        return moves

    def write(self, vals):
        """Ensure discount is reapplied when invoice changes."""
        res = super().write(vals)

        # If discount changed, recompute
        if 'global_discount_fixed' in vals:
            for move in self.filtered(lambda m: m.is_invoice() and m.state == 'draft'):
                _logger.info(f"Discount changed via write for {move.name}, recomputing")
                move._recompute_tax_lines()

        return res