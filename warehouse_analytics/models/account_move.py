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
        Override create to clean up analytic_distribution only for user-created invoices.
        Skip system-triggered creations to prevent relational SQL errors.
        """
        safe_vals_list = []

        for vals in vals_list:
            # Only clean up for customer/vendor invoices (not payments or internal moves)
            move_type = vals.get('move_type') or self._context.get('default_move_type')
            if move_type in ('out_invoice', 'in_invoice', 'out_refund', 'in_refund'):
                if 'invoice_line_ids' in vals:
                    cleaned_lines = []
                    for line_cmd in vals['invoice_line_ids']:
                        if isinstance(line_cmd, (list, tuple)) and len(line_cmd) >= 3:
                            if line_cmd[0] in (0, 1):  # create or update
                                line_vals = line_cmd[2] if isinstance(line_cmd[2], dict) else {}
                                # Remove problematic analytic keys
                                line_vals.pop('analytic_distribution', None)
                                line_vals.pop('analytic_account_id', None)
                                cleaned_lines.append((line_cmd[0], line_cmd[1] if len(line_cmd) > 1 else 0, line_vals))
                            else:
                                cleaned_lines.append(line_cmd)
                        else:
                            cleaned_lines.append(line_cmd)
                    vals['invoice_line_ids'] = cleaned_lines
            safe_vals_list.append(vals)

        return super(AccountMove, self).create(safe_vals_list)

    @api.onchange('warehouse_analytic_id')
    def _onchange_warehouse_analytic_id(self):
        """
        When user changes warehouse analytic in UI, apply it to invoice lines.
        """
        if self.warehouse_analytic_id and self.invoice_line_ids:
            analytic_distribution = {str(self.warehouse_analytic_id.id): 100}

            for line in self.invoice_line_ids.filtered(lambda l: not l.display_type):
                line.analytic_distribution = analytic_distribution

            _logger.info(
                f"Applied warehouse analytic '{self.warehouse_analytic_id.name}' "
                f"to {len(self.invoice_line_ids)} invoice lines."
            )

    def write(self, vals):
        """
        When warehouse_analytic_id is changed, update all analytic lines in draft state.
        """
        res = super(AccountMove, self).write(vals)

        if 'warehouse_analytic_id' in vals:
            for move in self.filtered(lambda m: m.state == 'draft' and m.warehouse_analytic_id):
                analytic_distribution = {str(move.warehouse_analytic_id.id): 100}

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

                    _logger.info(
                        f"Updated analytic for {len(invoice_line_ids)} lines in {move.name} "
                        f"({move.warehouse_analytic_id.name})"
                    )

        return res

    def _post(self, soft=True):
        """
        Apply warehouse analytic to ALL lines after posting.
        This ensures analytic consistency across all journal entries.
        """
        posted_moves = super(AccountMove, self)._post(soft)

        for move in posted_moves:
            if not move.warehouse_analytic_id:
                continue

            analytic_distribution = {str(move.warehouse_analytic_id.id): 100}

            line_ids_to_update = move.line_ids.filtered(
                lambda l: not l.analytic_distribution
            ).ids

            if line_ids_to_update:
                try:
                    query = """
                        UPDATE account_move_line
                        SET analytic_distribution = %s
                        WHERE id IN %s
                    """
                    self.env.cr.execute(query, (json.dumps(analytic_distribution), tuple(line_ids_to_update)))
                    move.line_ids.invalidate_recordset(['analytic_distribution'])

                    _logger.info(
                        f"✓ Move {move.name}: Applied '{move.warehouse_analytic_id.name}' "
                        f"to {len(line_ids_to_update)} lines."
                    )

                except Exception as e:
                    _logger.error(f"✗ Failed to apply analytic to {move.name}: {str(e)}")

        return posted_moves


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
        When user adds product, auto-apply warehouse analytic if available on parent move.
        """
        result = super(AccountMoveLine, self)._onchange_product_id()

        if (self.move_id.warehouse_analytic_id and
                not self.analytic_distribution and
                not self.display_type):
            self.analytic_distribution = {
                str(self.move_id.warehouse_analytic_id.id): 100
            }

        return result
