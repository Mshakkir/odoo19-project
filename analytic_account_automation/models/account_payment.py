from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, **kwargs):
        """
        Override to copy analytic distribution from invoice to payment journal entry
        This ensures payment lines inherit the same analytic account as the invoice
        """
        # Call parent method with all kwargs
        line_vals_list = super()._prepare_move_line_default_vals(
            write_off_line_vals=write_off_line_vals,
            **kwargs
        )

        # Get analytic distribution from the invoice being paid
        analytic_distribution = self._get_invoice_analytic_distribution()

        if analytic_distribution:
            _logger.info(f"Payment {self.name}: Found analytic distribution from invoice: {analytic_distribution}")

            # Apply analytic to all payment lines
            for line_vals in line_vals_list:
                # Only apply if line doesn't already have analytic set
                if not line_vals.get('analytic_distribution'):
                    line_vals['analytic_distribution'] = analytic_distribution
                    _logger.info(f"Applied analytic to payment line: Account={line_vals.get('account_id')}, "
                                 f"Debit={line_vals.get('debit', 0)}, Credit={line_vals.get('credit', 0)}")
        else:
            _logger.warning(f"Payment {self.name}: No analytic distribution found from invoice")

        return line_vals_list

    def _get_invoice_analytic_distribution(self):
        """
        Get analytic distribution from the invoice(s) being paid
        Returns the analytic distribution from the first invoice line with analytic
        """
        self.ensure_one()

        _logger.info(f"=" * 80)
        _logger.info(f"Getting analytic for payment: {self.name if self.name != '/' else 'NEW'}")

        # Get invoices being paid (for customer/supplier payments)
        invoices = self.reconciled_invoice_ids
        _logger.info(f"Reconciled invoices: {invoices.mapped('name')}")

        if not invoices:
            # If no reconciled invoices yet, try to get from context (during payment registration)
            invoice_ids = self._context.get('active_ids', [])
            _logger.info(f"Context active_ids: {invoice_ids}, active_model: {self._context.get('active_model')}")

            if invoice_ids and self._context.get('active_model') == 'account.move':
                invoices = self.env['account.move'].browse(invoice_ids)
                _logger.info(f"Found invoices from context: {invoices.mapped('name')}")

        if not invoices:
            _logger.warning(f"No invoices found for payment!")
            return False

        # Get the first invoice
        invoice = invoices[0]
        _logger.info(f"Checking invoice: {invoice.name}")

        # Get analytic from invoice product lines (not receivable/payable lines)
        product_lines = invoice.invoice_line_ids.filtered(
            lambda l: l.display_type == 'product' and l.analytic_distribution
        )

        _logger.info(f"Product lines with analytic: {len(product_lines)}")

        if product_lines:
            analytic_dist = product_lines[0].analytic_distribution
            _logger.info(f"✓ Found analytic from invoice {invoice.name}: {analytic_dist}")
            _logger.info(f"=" * 80)
            return analytic_dist

        # Fallback: try to get from receivable/payable line if it has analytic
        receivable_payable_lines = invoice.line_ids.filtered(
            lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
        )

        _logger.info(f"Receivable/payable lines: {len(receivable_payable_lines)}")

        if receivable_payable_lines and receivable_payable_lines[0].analytic_distribution:
            analytic_dist = receivable_payable_lines[0].analytic_distribution
            _logger.info(f"✓ Found analytic from receivable/payable line: {analytic_dist}")
            _logger.info(f"=" * 80)
            return analytic_dist

        _logger.warning(f"✗ No analytic distribution found for invoice {invoice.name}")
        _logger.info(f"=" * 80)
        return False

    def action_post(self):
        """
        After posting payment, ensure analytic is applied
        This is a safety check in case _prepare_move_line_default_vals didn't catch it
        """
        res = super().action_post()

        # Verify and fix analytic distribution after posting
        for payment in self:
            analytic_distribution = payment._get_invoice_analytic_distribution()

            if analytic_distribution:
                # Update move lines that are missing analytic
                lines_to_update = payment.move_id.line_ids.filtered(
                    lambda l: not l.analytic_distribution and
                              l.account_id.account_type in ('asset_cash', 'liability_credit_card',
                                                            'asset_receivable', 'liability_payable')
                )

                if lines_to_update:
                    # Use SQL update to bypass restrictions
                    import json
                    analytic_json = json.dumps(analytic_distribution) if isinstance(analytic_distribution,
                                                                                    dict) else analytic_distribution

                    self.env.cr.execute("""
                        UPDATE account_move_line
                        SET analytic_distribution = %s::jsonb
                        WHERE id IN %s
                    """, (analytic_json, tuple(lines_to_update.ids)))

                    _logger.info(f"Post-posting fix: Updated {len(lines_to_update)} payment lines with analytic")

                    # Invalidate cache
                    lines_to_update.invalidate_recordset(['analytic_distribution'])
                    self.env.cr.commit()

        return res


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _stock_account_prepare_anglo_saxon_out_lines_vals(self):
        """
        Override to ensure analytic is copied to COGS lines in sales invoices
        """
        lines_vals_list = super()._stock_account_prepare_anglo_saxon_out_lines_vals()

        # Get analytic from invoice lines
        for move in self:
            product_lines = move.invoice_line_ids.filtered(
                lambda l: l.display_type == 'product' and l.analytic_distribution
            )

            if product_lines and lines_vals_list:
                analytic_dist = product_lines[0].analytic_distribution

                # Apply to COGS lines
                for line_vals in lines_vals_list:
                    if not line_vals.get('analytic_distribution'):
                        line_vals['analytic_distribution'] = analytic_dist

        return lines_vals_list