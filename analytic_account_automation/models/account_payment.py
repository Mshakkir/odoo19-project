from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def write(self, vals):
        """Apply analytic when payment moves are created"""
        res = super().write(vals)

        # When move_id is set, apply analytic
        if 'move_id' in vals:
            for payment in self:
                payment._apply_analytic_to_move()

        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Apply analytic after payment is created"""
        payments = super().create(vals_list)

        for payment in payments:
            if payment.move_id:
                payment._apply_analytic_to_move()

        return payments

    def _apply_analytic_to_move(self):
        """
        Apply analytic distribution from invoice to payment move lines
        This runs AFTER the journal entry is created
        """
        self.ensure_one()

        if not self.move_id:
            return

        _logger.info(f"=" * 80)
        _logger.info(f"Applying analytic to payment {self.name}")

        # Get the invoice
        invoices = self.reconciled_invoice_ids or self.reconciled_bill_ids

        if not invoices:
            # Try from context
            invoice_ids = self._context.get('active_ids', [])
            if invoice_ids and self._context.get('active_model') == 'account.move':
                invoices = self.env['account.move'].browse(invoice_ids)

        if not invoices:
            _logger.warning(f"No invoice found for payment {self.name}")
            _logger.info(f"=" * 80)
            return

        invoice = invoices[0]
        _logger.info(f"Source invoice: {invoice.name}")

        # Get analytic from invoice product lines
        analytic_distribution = False
        for line in invoice.invoice_line_ids:
            if line.display_type == 'product' and line.analytic_distribution:
                analytic_distribution = line.analytic_distribution
                _logger.info(f"✓ Found analytic from line '{line.name}': {analytic_distribution}")
                break

        if not analytic_distribution:
            _logger.warning(f"No analytic found on invoice {invoice.name}")
            _logger.info(f"=" * 80)
            return

        # Apply to receivable/payable lines that don't have analytic
        lines_updated = 0
        for line in self.move_id.line_ids:
            if line.account_id.account_type in ('asset_receivable', 'liability_payable'):
                if not line.analytic_distribution:
                    line.analytic_distribution = analytic_distribution
                    lines_updated += 1
                    _logger.info(f"✓ Updated line: {line.account_id.code} - {line.account_id.name}")

        if lines_updated:
            _logger.info(f"✓✓✓ SUCCESS: Updated {lines_updated} lines with analytic")
        else:
            _logger.warning(f"No lines were updated")

        _logger.info(f"=" * 80)


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def _create_payments(self):
        """Ensure analytic is applied after payment creation"""
        _logger.info(f"Creating payment from register")
        _logger.info(f"Active IDs: {self._context.get('active_ids')}")
        _logger.info(f"Active Model: {self._context.get('active_model')}")

        # Create payments
        payments = super()._create_payments()

        # Apply analytic to each payment
        for payment in payments:
            _logger.info(f"Processing payment: {payment.name}")
            payment._apply_analytic_to_move()

        return payments