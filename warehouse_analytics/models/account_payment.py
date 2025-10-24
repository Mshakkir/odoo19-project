# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    warehouse_analytic_id = fields.Many2one(
        'account.analytic.account',
        string='Warehouse / Branch',
        compute='_compute_warehouse_analytic',
        store=True,
        readonly=False,
        tracking=True,
        help='Inherited from related invoice(s). Can be changed manually if needed.'
    )

    @api.depends('reconciled_invoice_ids', 'reconciled_invoice_ids.warehouse_analytic_id')
    def _compute_warehouse_analytic(self):
        """
        When payment is linked to invoices, inherit warehouse analytic from them.
        """
        for payment in self:
            if payment.reconciled_invoice_ids:
                # Get warehouse analytic from first invoice
                first_invoice = payment.reconciled_invoice_ids[0]
                if first_invoice.warehouse_analytic_id:
                    payment.warehouse_analytic_id = first_invoice.warehouse_analytic_id
                    _logger.info(
                        f"Payment {payment.name} inherited warehouse analytic "
                        f"'{first_invoice.warehouse_analytic_id.name}' from invoice {first_invoice.name}"
                    )
                else:
                    payment.warehouse_analytic_id = False
            else:
                payment.warehouse_analytic_id = False

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        """
        Ensure ALL payment journal entries get warehouse analytic.
        This includes:
        - Bank/Cash debit/credit lines
        - Receivable/Payable clearing lines
        - Write-off lines (if any)
        """
        line_vals = super(AccountPayment, self)._prepare_move_line_default_vals(write_off_line_vals)

        # Determine which analytic to use
        analytic_distribution = None

        # Priority 1: Use warehouse analytic from payment record
        if self.warehouse_analytic_id:
            analytic_distribution = {str(self.warehouse_analytic_id.id): 100}
            _logger.info(f"Payment {self.name} using warehouse analytic from payment record")

        # Priority 2: Get from reconciled invoices
        elif self.reconciled_invoice_ids:
            for invoice in self.reconciled_invoice_ids:
                if invoice.warehouse_analytic_id:
                    analytic_distribution = {str(invoice.warehouse_analytic_id.id): 100}
                    _logger.info(
                        f"Payment {self.name} using warehouse analytic from invoice {invoice.name}"
                    )
                    break

        # Priority 3: Get from reconciled bills
        elif self.reconciled_bill_ids:
            for bill in self.reconciled_bill_ids:
                if bill.warehouse_analytic_id:
                    analytic_distribution = {str(bill.warehouse_analytic_id.id): 100}
                    _logger.info(
                        f"Payment {self.name} using warehouse analytic from bill {bill.name}"
                    )
                    break

        # Apply analytic distribution to ALL payment lines
        if analytic_distribution:
            for line in line_vals:
                if not line.get('analytic_distribution'):
                    line['analytic_distribution'] = analytic_distribution

                    if line.get('account_id'):
                        account = self.env['account.account'].browse(line['account_id'])
                        _logger.debug(
                            f"Applied analytic to payment line: {account.code} - {account.name}"
                        )

        return line_vals

    def action_post(self):
        """
        After posting payment, ensure analytic is applied to all lines.
        This is a safety net in case _prepare_move_line_default_vals didn't catch everything.
        """
        res = super(AccountPayment, self).action_post()

        for payment in self:
            if payment.warehouse_analytic_id and payment.move_id:
                analytic_distribution = {str(payment.warehouse_analytic_id.id): 100}

                # Find lines without analytic
                lines_without_analytic = payment.move_id.line_ids.filtered(
                    lambda l: not l.analytic_distribution
                )

                if lines_without_analytic:
                    lines_without_analytic.write({
                        'analytic_distribution': analytic_distribution
                    })
                    _logger.info(
                        f"Post-payment: Applied analytic to {len(lines_without_analytic)} lines "
                        f"in payment {payment.name}"
                    )

        return res


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement.line'

    def _prepare_move_line_default_vals(self, move, **kwargs):
        """
        For bank statement reconciliation, try to inherit analytic from matched invoice.
        """
        line_vals = super(AccountBankStatement, self)._prepare_move_line_default_vals(
            move, **kwargs
        )

        # Try to get analytic from payment if available
        if self.payment_id and self.payment_id.warehouse_analytic_id:
            analytic_distribution = {str(self.payment_id.warehouse_analytic_id.id): 100}

            for line in line_vals:
                if not line.get('analytic_distribution'):
                    line['analytic_distribution'] = analytic_distribution

        return line_vals