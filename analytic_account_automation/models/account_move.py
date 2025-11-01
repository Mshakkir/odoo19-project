from odoo import models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _recompute_dynamic_lines(self, recompute_all_taxes=False, recompute_tax_base_amount=False):
        """
        Override to automatically set analytic distribution on receivable/payable lines.
        This method is called when invoice is saved or confirmed.
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

                    # Set on receivable/payable lines
                    for line in move.line_ids.filtered(
                            lambda l: l.account_id.account_type in ['asset_receivable', 'liability_payable']
                    ):
                        line.analytic_distribution = analytic_distribution

        return res