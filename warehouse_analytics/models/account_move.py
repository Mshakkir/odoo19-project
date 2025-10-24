# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
import json

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

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to clean up any problematic analytic_distribution values.
        """
        # CRITICAL: Remove analytic_distribution from invoice lines during creation
        for vals in vals_list:
            if 'invoice_line_ids' in vals:
                for line_cmd in vals['invoice_line_ids']:
                    if isinstance(line_cmd, (list, tuple)) and len(line_cmd) >= 3:
                        if line_cmd[0] in (0, 1):  # Create or Update command
                            line_vals = line_cmd[2] if isinstance(line_cmd[2], dict) else {}
                            # Remove problematic fields
                            line_vals.pop('analytic_distribution', None)
                            line_vals.pop('analytic_account_id', None)

        # Create invoice normally
        return super(AccountMove, self).create(vals_list)

    @api.onchange('warehouse_analytic_id')
    def _onchange_warehouse_analytic_id(self):
        """
        When user changes warehouse analytic in UI, apply it to invoice lines.
        """
        if self.warehouse_analytic_id and self.invoice_line_ids:
            analytic_distribution = {str(self.warehouse_analytic_id.id): 100}

            for line in self.invoice_line_ids.filtered(lambda l: not l.display_type):
                line.analytic_distribution = analytic_distribution

            _logger.info(f"Applied warehouse analytic {self.warehouse_analytic_id.name} "
                         f"to {len(self.invoice_line_ids)} invoice lines")

    def write(self, vals):
        """
        When warehouse_analytic_id is written, apply to all lines in draft state.
        """
        res = super(AccountMove, self).write(vals)

        if 'warehouse_analytic_id' in vals:
            for move in self.filtered(lambda m: m.state == 'draft' and m.warehouse_analytic_id):
                analytic_distribution = {str(move.warehouse_analytic_id.id): 100}

                # Apply to invoice lines using direct SQL to avoid ORM issues
                invoice_line_ids = move.invoice_line_ids.filtered(
                    lambda l: not l.display_type
                ).ids

                if invoice_line_ids:
                    query = """
                        UPDATE account_move_line 
                        SET analytic_distribution = %s
                        WHERE id IN %s
                    """
                    self.env.cr.execute(query, (json.dumps(analytic_distribution), tuple(invoice_line_ids)))
                    move.invoice_line_ids.invalidate_recordset(['analytic_distribution'])

                    _logger.info(f"Applied warehouse analytic to {len(invoice_line_ids)} lines in {move.name}")

        return res

    def _post(self, soft=True):
        """
        MAIN METHOD: Apply warehouse analytic to ALL lines after posting.

        This is the safest approach - we let Odoo create all automatic entries first,
        then we apply the analytic to everything.
        """
        # Post the invoice first
        posted_moves = super(AccountMove, self)._post(soft)

        # Now apply analytics to all lines
        for move in posted_moves:
            if not move.warehouse_analytic_id:
                continue

            analytic_distribution = {str(move.warehouse_analytic_id.id): 100}

            # Get ALL line IDs that need analytic
            line_ids_to_update = move.line_ids.filtered(
                lambda l: not l.analytic_distribution
            ).ids

            if line_ids_to_update:
                try:
                    # Use direct SQL UPDATE - most reliable method
                    query = """
                        UPDATE account_move_line 
                        SET analytic_distribution = %s
                        WHERE id IN %s
                    """
                    self.env.cr.execute(query, (
                        json.dumps(analytic_distribution),
                        tuple(line_ids_to_update)
                    ))

                    # Invalidate cache
                    move.line_ids.invalidate_recordset(['analytic_distribution'])

                    _logger.info(
                        f"✓ Move {move.name}: Applied '{move.warehouse_analytic_id.name}' "
                        f"to {len(line_ids_to_update)} lines"
                    )

                except Exception as e:
                    _logger.error(f"✗ Failed to apply analytic to {move.name}: {str(e)}")

        return posted_moves


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
        When user adds product in UI, apply warehouse analytic if available.
        """
        result = super(AccountMoveLine, self)._onchange_product_id()

        if (self.move_id.warehouse_analytic_id and
                not self.analytic_distribution and
                not self.display_type):
            self.analytic_distribution = {
                str(self.move_id.warehouse_analytic_id.id): 100
            }

        return result