# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    warehouse_analytic_id = fields.Many2one(
        'account.analytic.account',
        string='Warehouse / Branch',
        tracking=True,
        copy=True,
        help='Select warehouse/branch for proper financial reporting segregation. '
             'This will be applied to ALL journal entries including receivables and payables.'
    )

    @api.onchange('warehouse_analytic_id')
    def _onchange_warehouse_analytic_id(self):
        """
        When user changes warehouse analytic, apply it to all invoice lines immediately.
        This ensures consistency before posting.
        """
        if self.warehouse_analytic_id and self.invoice_line_ids:
            analytic_distribution = {str(self.warehouse_analytic_id.id): 100}

            for line in self.invoice_line_ids:
                line.analytic_distribution = analytic_distribution

            _logger.info(f"Applied warehouse analytic {self.warehouse_analytic_id.name} "
                         f"to {len(self.invoice_line_ids)} invoice lines")

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to propagate warehouse analytic to invoice lines on creation.
        This handles cases where invoice is created programmatically (like from SO/PO).
        """
        for vals in vals_list:
            if vals.get('warehouse_analytic_id') and vals.get('invoice_line_ids'):
                analytic_id = vals['warehouse_analytic_id']
                analytic_distribution = {str(analytic_id): 100}

                # vals['invoice_line_ids'] format: [(0, 0, {...}), (0, 0, {...}), ...]
                for line_cmd in vals['invoice_line_ids']:
                    if line_cmd[0] == 0:  # Create command (0, 0, {...})
                        if 'analytic_distribution' not in line_cmd[2]:
                            line_cmd[2]['analytic_distribution'] = analytic_distribution

                _logger.info(f"Warehouse analytic {analytic_id} applied to invoice lines on creation")

        return super(AccountMove, self).create(vals_list)

    def write(self, vals):
        """
        If warehouse analytic is changed, update all related lines.
        """
        res = super(AccountMove, self).write(vals)

        if 'warehouse_analytic_id' in vals:
            for move in self:
                if move.warehouse_analytic_id and move.state == 'draft':
                    analytic_distribution = {str(move.warehouse_analytic_id.id): 100}

                    # Update invoice lines
                    move.invoice_line_ids.write({
                        'analytic_distribution': analytic_distribution
                    })

                    _logger.info(f"Updated warehouse analytic for move {move.name}")

        return res

    def _post(self, soft=True):
        """
        CRITICAL METHOD: This is where the magic happens!

        After invoice is posted, Odoo automatically creates:
        - Receivable/Payable lines (for customers/vendors)
        - Tax lines (VAT input/output)
        - Rounding lines

        We need to ensure ALL these automatic lines get the warehouse analytic.
        """
        # First, post the move using standard Odoo logic
        posted_moves = super(AccountMove, self)._post(soft)

        # Now apply warehouse analytic to ALL lines
        for move in posted_moves:
            if not move.warehouse_analytic_id:
                continue  # Skip if no warehouse analytic set

            analytic_distribution = {str(move.warehouse_analytic_id.id): 100}

            # Find all lines that don't have analytic distribution
            lines_without_analytic = move.line_ids.filtered(
                lambda l: not l.analytic_distribution
            )

            if lines_without_analytic:
                # Apply warehouse analytic to these lines
                lines_without_analytic.write({
                    'analytic_distribution': analytic_distribution
                })

                _logger.info(
                    f"Move {move.name}: Applied warehouse analytic '{move.warehouse_analytic_id.name}' "
                    f"to {len(lines_without_analytic)} lines including receivables/payables/taxes"
                )

                # Log which account types were updated
                account_types = lines_without_analytic.mapped('account_id.account_type')
                _logger.info(f"Account types updated: {', '.join(set(account_types))}")

        return posted_moves

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        """
        This method is called BEFORE posting to prepare all journal entry lines.
        We intercept here to add analytic to receivable/payable lines.

        This is a backup method in case _post() doesn't catch everything.
        """
        lines = super(AccountMove, self)._prepare_move_line_default_vals(write_off_line_vals)

        if self.warehouse_analytic_id:
            analytic_distribution = {str(self.warehouse_analytic_id.id): 100}

            for line_vals in lines:
                # Check if line is for a balance sheet account that needs analytic
                if line_vals.get('account_id'):
                    account = self.env['account.account'].browse(line_vals['account_id'])

                    # Apply to receivables, payables, bank accounts, etc.
                    if account.account_type in [
                        'asset_receivable',  # Account Receivable
                        'liability_payable',  # Account Payable
                        'asset_cash',  # Bank & Cash accounts
                        'asset_current',  # Current Assets
                        'liability_current',  # Current Liabilities
                    ]:
                        if 'analytic_distribution' not in line_vals:
                            line_vals['analytic_distribution'] = analytic_distribution
                            _logger.debug(
                                f"Pre-assigned analytic to {account.code} - {account.name}"
                            )

        return lines


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
        When user adds a product to invoice line, auto-set warehouse analytic
        from the invoice header.
        """
        result = super(AccountMoveLine, self)._onchange_product_id()

        # If invoice has warehouse analytic and this line doesn't, apply it
        if (self.move_id.warehouse_analytic_id and
                not self.analytic_distribution and
                not self.display_type):  # Skip section/note lines

            self.analytic_distribution = {
                str(self.move_id.warehouse_analytic_id.id): 100
            }

            _logger.debug(
                f"Auto-applied warehouse analytic to line with product {self.product_id.name}"
            )

        return result

    @api.onchange('account_id')
    def _onchange_account_id(self):
        """
        When user changes account on a line, maintain warehouse analytic.
        """
        result = super(AccountMoveLine, self)._onchange_account_id()

        # Maintain warehouse analytic when account changes
        if (self.move_id.warehouse_analytic_id and
                not self.analytic_distribution and
                self.account_id):
            self.analytic_distribution = {
                str(self.move_id.warehouse_analytic_id.id): 100
            }

        return result