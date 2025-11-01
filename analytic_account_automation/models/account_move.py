from odoo import models, api, Command


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _recompute_dynamic_lines(self, recompute_all_taxes=False, recompute_tax_base_amount=False):
        """
        Override to set analytic distribution on receivable/payable lines
        """
        res = super()._recompute_dynamic_lines(
            recompute_all_taxes=recompute_all_taxes,
            recompute_tax_base_amount=recompute_tax_base_amount
        )

        for move in self:
            if move.move_type in ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']:
                # Get analytic from product lines
                product_lines = move.invoice_line_ids.filtered(
                    lambda l: l.display_type == 'product' and l.analytic_distribution
                )

                if product_lines:
                    analytic_distribution = product_lines[0].analytic_distribution

                    # Update receivable/payable lines with context to bypass checks
                    receivable_payable_lines = move.line_ids.filtered(
                        lambda l: l.account_id.account_type in ['asset_receivable', 'liability_payable']
                    )

                    if receivable_payable_lines:
                        # Use sudo() and special context to force the update
                        receivable_payable_lines.sudo().with_context(
                            check_move_validity=False,
                            skip_invoice_sync=True,
                            skip_account_move_synchronization=True
                        ).write({
                            'analytic_distribution': analytic_distribution
                        })

        return res

    def _inverse_amount_total(self):
        """Override to maintain analytic when amount changes"""
        for move in self:
            # Store current analytic before parent method
            analytic_map = {}
            for line in move.line_ids:
                if line.account_id.account_type in ['asset_receivable', 'liability_payable']:
                    analytic_map[line.id] = line.analytic_distribution

        # Call parent
        res = super()._inverse_amount_total()

        # Restore analytic after parent method
        for move in self:
            for line in move.line_ids:
                if line.id in analytic_map and analytic_map[line.id]:
                    line.with_context(
                        check_move_validity=False
                    ).analytic_distribution = analytic_map[line.id]

        return res


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('move_id', 'product_id', 'analytic_distribution')
    def _compute_all_tax(self):
        """Override to preserve analytic distribution"""
        # Store analytic before compute
        analytic_map = {line.id: line.analytic_distribution for line in self}

        # Call parent
        res = super()._compute_all_tax()

        # Restore analytic after compute
        for line in self:
            if line.id in analytic_map and analytic_map[line.id]:
                if line.account_id.account_type in ['asset_receivable', 'liability_payable']:
                    line.analytic_distribution = analytic_map[line.id]

        return res