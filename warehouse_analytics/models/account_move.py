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
        help='Select warehouse/branch for financial segregation. '
             'This applies to all journal entries including receivables and payables.'
    )

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to safely clean analytic fields on invoice lines.
        Avoid relational errors during system-triggered invoice creation.
        """
        for vals in vals_list:
            move_type = vals.get('move_type') or self._context.get('default_move_type')
            if move_type in ('out_invoice', 'in_invoice', 'out_refund', 'in_refund'):
                if 'invoice_line_ids' in vals:
                    cleaned_lines = []
                    for cmd in vals['invoice_line_ids']:
                        if isinstance(cmd, (list, tuple)) and len(cmd) >= 3:
                            if cmd[0] in (0, 1):  # create or update
                                line_vals = dict(cmd[2] or {})
                                # Remove problematic analytic keys
                                line_vals.pop('analytic_distribution', None)
                                line_vals.pop('analytic_account_id', None)
                                cleaned_lines.append((cmd[0], cmd[1] if len(cmd) > 1 else 0, line_vals))
                            else:
                                cleaned_lines.append(cmd)
                        else:
                            cleaned_lines.append(cmd)
                    vals['invoice_line_ids'] = cleaned_lines

        moves = super().create(vals_list)

        # Auto-apply warehouse analytic if present
        for move in moves:
            if move.warehouse_analytic_id:
                analytic_distribution = {str(move.warehouse_analytic_id.id): 100}
                move.line_ids.filtered(lambda l: not l.display_type).write({
                    'analytic_distribution': json.dumps(analytic_distribution)
                })
                _logger.info(f"✓ Applied analytic {move.warehouse_analytic_id.name} on creation for {move.name}")

        return moves

    @api.onchange('warehouse_analytic_id')
    def _onchange_warehouse_analytic_id(self):
        """Apply warehouse analytic to invoice lines when changed in UI."""
        if self.warehouse_analytic_id and self.invoice_line_ids:
            analytic_distribution = {str(self.warehouse_analytic_id.id): 100}
            self.invoice_line_ids.filtered(lambda l: not l.display_type).write({
                'analytic_distribution': json.dumps(analytic_distribution)
            })
            _logger.info(f"✓ Updated {len(self.invoice_line_ids)} lines for {self.name}")

    def write(self, vals):
        """If warehouse analytic changes, propagate to draft invoice lines."""
        res = super().write(vals)
        if 'warehouse_analytic_id' in vals:
            for move in self.filtered(lambda m: m.state == 'draft' and m.warehouse_analytic_id):
                analytic_distribution = {str(move.warehouse_analytic_id.id): 100}
                line_ids = move.invoice_line_ids.filtered(lambda l: not l.display_type).ids
                if line_ids:
                    self.env.cr.execute("""
                        UPDATE account_move_line
                        SET analytic_distribution = %s
                        WHERE id IN %s
                    """, (json.dumps(analytic_distribution), tuple(line_ids)))
                    move.invoice_line_ids.invalidate_recordset(['analytic_distribution'])
                    _logger.info(f"✓ Updated analytic for {len(line_ids)} lines in {move.name}")
        return res

    def _post(self, soft=True):
        """After posting, ensure all lines inherit the warehouse analytic."""
        posted_moves = super()._post(soft)
        for move in posted_moves:
            if move.warehouse_analytic_id:
                analytic_distribution = {str(move.warehouse_analytic_id.id): 100}
                line_ids = move.line_ids.filtered(lambda l: not l.analytic_distribution).ids
                if line_ids:
                    try:
                        self.env.cr.execute("""
                            UPDATE account_move_line
                            SET analytic_distribution = %s
                            WHERE id IN %s
                        """, (json.dumps(analytic_distribution), tuple(line_ids)))
                        move.line_ids.invalidate_recordset(['analytic_distribution'])
                        _logger.info(f"✓ Move {move.name}: Applied analytic {move.warehouse_analytic_id.name}")
                    except Exception as e:
                        _logger.error(f"✗ Failed to apply analytic for {move.name}: {str(e)}")
        return posted_moves


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Auto-apply warehouse analytic when adding products."""
        res = super()._onchange_product_id()
        if self.move_id.warehouse_analytic_id and not self.display_type:
            analytic_distribution = {str(self.move_id.warehouse_analytic_id.id): 100}
            self.analytic_distribution = analytic_distribution
        return res
