from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _recompute_dynamic_lines(self, recompute_all_taxes=False, recompute_tax_base_amount=False):
        """Override with debug logging"""
        _logger.info("=" * 50)
        _logger.info("RECOMPUTE DYNAMIC LINES CALLED")
        _logger.info("=" * 50)

        res = super()._recompute_dynamic_lines(
            recompute_all_taxes=recompute_all_taxes,
            recompute_tax_base_amount=recompute_tax_base_amount
        )

        for move in self:
            _logger.info(f"Processing move: {move.name}")
            _logger.info(f"Move type: {move.move_type}")

            if move.move_type in ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']:
                # Check invoice lines
                _logger.info(f"Total invoice lines: {len(move.invoice_line_ids)}")

                product_lines = move.invoice_line_ids.filtered(
                    lambda l: l.display_type == 'product' and l.analytic_distribution
                )
                _logger.info(f"Product lines with analytic: {len(product_lines)}")

                if product_lines:
                    analytic_distribution = product_lines[0].analytic_distribution
                    _logger.info(f"Analytic distribution to copy: {analytic_distribution}")

                    # Check journal items
                    _logger.info(f"Total journal lines: {len(move.line_ids)}")

                    receivable_payable_lines = move.line_ids.filtered(
                        lambda l: l.account_id.account_type in ['asset_receivable', 'liability_payable']
                    )
                    _logger.info(f"Receivable/Payable lines found: {len(receivable_payable_lines)}")

                    for line in receivable_payable_lines:
                        _logger.info(f"Setting analytic on: {line.account_id.code} - {line.account_id.name}")
                        line.analytic_distribution = analytic_distribution
                        _logger.info(f"Analytic set successfully: {line.analytic_distribution}")
                else:
                    _logger.warning("No product lines with analytic distribution found!")

        _logger.info("=" * 50)
        return res