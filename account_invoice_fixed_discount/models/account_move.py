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

    def _compute_amount(self):
        """
        Override to apply global discount after standard computation.
        """
        # Let Odoo compute standard amounts first
        super(AccountMove, self)._compute_amount()

        # Apply our global discount
        for move in self:
            # Only process invoices with discount
            if not move.is_invoice() or not move.global_discount_fixed or move.global_discount_fixed <= 0:
                continue

            # Get product lines
            product_lines = move.invoice_line_ids.filtered(lambda l: not l.display_type)
            if not product_lines:
                continue

            # Calculate original amounts
            original_subtotal = sum(product_lines.mapped('price_subtotal'))
            original_total_with_tax = sum(product_lines.mapped('price_total'))
            original_tax = original_total_with_tax - original_subtotal

            # Skip if zero
            if original_subtotal <= 0:
                continue

            # Apply discount
            new_subtotal = original_subtotal - move.global_discount_fixed
            if new_subtotal < 0:
                new_subtotal = 0.0

            # Proportional tax
            discount_ratio = new_subtotal / original_subtotal if original_subtotal > 0 else 0.0
            new_tax = original_tax * discount_ratio
            new_total = new_subtotal + new_tax

            # Round
            currency = move.currency_id or move.company_id.currency_id
            move.amount_untaxed = currency.round(new_subtotal)
            move.amount_tax = currency.round(new_tax)
            move.amount_total = currency.round(new_total)
            move.amount_residual = currency.round(new_total)

            _logger.warning(
                f"✅ DISCOUNT: {move.name or 'New'} | "
                f"Original={original_subtotal:.2f} - Discount={move.global_discount_fixed:.2f} = "
                f"New={new_subtotal:.2f} + Tax={new_tax:.2f} = Total={new_total:.2f}"
            )

    @api.onchange('global_discount_fixed')
    def _onchange_global_discount_fixed(self):
        """Recalculate when discount changes in UI."""
        if self.is_invoice():
            # Just trigger the compute
            self._compute_amount()

    def _post(self, soft=True):
        """Override posting to ensure discount is applied before posting."""
        # Apply discount one more time before posting
        for move in self:
            if move.is_invoice() and move.global_discount_fixed and move.global_discount_fixed > 0:
                _logger.info(f"Applying discount before posting {move.name}")
                move._compute_amount()

        return super(AccountMove, self)._post(soft=soft)