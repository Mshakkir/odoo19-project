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

            for line in self.invoice_line_ids.filtered(lambda l: not l.display_type):
                line.analytic_distribution = analytic_distribution

            _logger.info(f"Applied warehouse analytic {self.warehouse_analytic_id.name} "
                         f"to {len(self.invoice_line_ids)} invoice lines")

    def write(self, vals):
        """
        If warehouse analytic is changed, update all related lines.
        """
        res = super(AccountMove, self).write(vals)

        if 'warehouse_analytic_id' in vals:
            for move in self:
                if move.warehouse_analytic_id and move.state == 'draft':
                    analytic_distribution = {str(move.warehouse_analytic_id.id): 100}

                    # Update invoice lines (exclude display lines like section/note)
                    lines_to_update = move.invoice_line_ids.filtered(lambda l: not l.display_type)
                    if lines_to_update:
                        lines_to_update.write({
                            'analytic_distribution': analytic_distribution
                        })

                    _logger.info(f"Updated warehouse analytic for move {move.name}")

        return res

    def _post(self, soft=True):
        """
        CRITICAL METHOD: Apply warehouse analytic to ALL journal entry lines.

        This runs AFTER the invoice is posted and all automatic lines are created.
        We apply the analytic to:
        - Receivable/Payable lines (automatic)
        - Tax lines (automatic)
        - Any other lines without analytics
        """
        # First, post the move using standard Odoo logic
        posted_moves = super(AccountMove, self)._post(soft)

        # Now apply warehouse analytic to ALL lines that don't have it
        for move in posted_moves:
            if not move.warehouse_analytic_id:
                continue  # Skip if no warehouse analytic set

            analytic_distribution = {str(move.warehouse_analytic_id.id): 100}

            # Find all lines without analytic distribution
            lines_without_analytic = move.line_ids.filtered(
                lambda l: not l.analytic_distribution
            )

            if lines_without_analytic:
                try:
                    # Use SQL to update directly - faster and avoids ORM issues
                    line_ids = tuple(lines_without_analytic.ids)
                    if line_ids:
                        # Update analytic_distribution using SQL
                        query = """
                            UPDATE account_move_line 
                            SET analytic_distribution = %s
                            WHERE id IN %s
                        """
                        import json
                        self.env.cr.execute(query, (json.dumps(analytic_distribution), line_ids))

                        # Invalidate cache to reflect changes
                        lines_without_analytic.invalidate_recordset(['analytic_distribution'])

                        _logger.info(
                            f"Move {move.name}: Applied warehouse analytic '{move.warehouse_analytic_id.name}' "
                            f"to {len(lines_without_analytic)} lines (receivables/payables/taxes)"
                        )
                except Exception as e:
                    _logger.error(f"Error applying analytic to lines: {str(e)}")
                    # Fallback to ORM write
                    try:
                        lines_without_analytic.write({
                            'analytic_distribution': analytic_distribution
                        })
                    except Exception as e2:
                        _logger.error(f"Fallback write also failed: {str(e2)}")

        return posted_moves


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
                not self.display_type):
            self.analytic_distribution = {
                str(self.move_id.warehouse_analytic_id.id): 100
            }

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
                self.account_id and
                not self.display_type):
            self.analytic_distribution = {
                str(self.move_id.warehouse_analytic_id.id): 100
            }

        return result