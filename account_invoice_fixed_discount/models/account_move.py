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
        THE NUCLEAR OPTION: Override and don't call super for invoices with discount.
        We compute everything from scratch.
        """
        # Separate moves with and without discount
        moves_with_discount = self.filtered(
            lambda m: m.is_invoice() and m.global_discount_fixed and m.global_discount_fixed > 0
        )
        moves_without_discount = self - moves_with_discount

        # Let Odoo handle normal moves
        if moves_without_discount:
            super(AccountMove, moves_without_discount)._compute_amount()

        # Handle discounted moves ourselves
        for move in moves_with_discount:
            product_lines = move.invoice_line_ids.filtered(lambda l: not l.display_type)

            if not product_lines:
                # No lines yet, use super
                super(AccountMove, move)._compute_amount()
                continue

            # Calculate from lines
            subtotal = sum(product_lines.mapped('price_subtotal'))
            total_with_tax = sum(product_lines.mapped('price_total'))
            tax_amount = total_with_tax - subtotal

            # Apply discount
            new_subtotal = subtotal - move.global_discount_fixed
            if new_subtotal < 0:
                new_subtotal = 0.0

            # Proportional tax
            if subtotal > 0:
                discount_ratio = new_subtotal / subtotal
                new_tax = tax_amount * discount_ratio
            else:
                new_tax = 0.0

            new_total = new_subtotal + new_tax

            # Round
            currency = move.currency_id or move.company_id.currency_id

            # THIS IS THE KEY: We directly set the values
            vals = {
                'amount_untaxed': currency.round(new_subtotal),
                'amount_tax': currency.round(new_tax),
                'amount_total': currency.round(new_total),
                'amount_residual': currency.round(new_total),
                'amount_untaxed_signed': currency.round(new_subtotal) * (
                    1 if move.move_type in ('out_invoice', 'in_refund') else -1),
                'amount_total_signed': currency.round(new_total) * (
                    1 if move.move_type in ('out_invoice', 'in_refund') else -1),
                'amount_total_in_currency_signed': currency.round(new_total) * (
                    1 if move.move_type in ('out_invoice', 'in_refund') else -1),
            }

            # Use SQL update to bypass ORM and avoid recursion
            self.env.cr.execute("""
                UPDATE account_move
                SET amount_untaxed = %s,
                    amount_tax = %s,
                    amount_total = %s,
                    amount_residual = %s,
                    amount_untaxed_signed = %s,
                    amount_total_signed = %s,
                    amount_total_in_currency_signed = %s
                WHERE id = %s
            """, (
                vals['amount_untaxed'],
                vals['amount_tax'],
                vals['amount_total'],
                vals['amount_residual'],
                vals['amount_untaxed_signed'],
                vals['amount_total_signed'],
                vals['amount_total_in_currency_signed'],
                move.id
            ))

            # Invalidate cache so Odoo reloads from database
            move.invalidate_recordset(['amount_untaxed', 'amount_tax', 'amount_total', 'amount_residual',
                                       'amount_untaxed_signed', 'amount_total_signed',
                                       'amount_total_in_currency_signed'])

            _logger.warning(
                f"🔥 NUCLEAR DISCOUNT APPLIED to {move.name or move.id}: "
                f"Subtotal={new_subtotal:.2f}, Tax={new_tax:.2f}, Total={new_total:.2f}"
            )

    @api.onchange('global_discount_fixed')
    def _onchange_global_discount_fixed(self):
        """Trigger recomputation when discount changes."""
        if self.is_invoice():
            self._compute_amount()

    @api.model_create_multi
    def create(self, vals_list):
        """Apply discount after creation."""
        moves = super(AccountMove, self).create(vals_list)

        # Recompute for moves with discount
        discounted_moves = moves.filtered(
            lambda m: m.is_invoice() and m.global_discount_fixed and m.global_discount_fixed > 0
        )
        if discounted_moves:
            _logger.info(f"Recomputing {len(discounted_moves)} invoices with discount")
            discounted_moves._compute_amount()

        return moves

    def write(self, vals):
        """Recompute when discount changes."""
        res = super(AccountMove, self).write(vals)

        if 'global_discount_fixed' in vals or 'invoice_line_ids' in vals:
            discounted_moves = self.filtered(
                lambda
                    m: m.is_invoice() and m.state == 'draft' and m.global_discount_fixed and m.global_discount_fixed > 0
            )
            if discounted_moves:
                _logger.info(f"Recomputing after write")
                discounted_moves._compute_amount()

        return res