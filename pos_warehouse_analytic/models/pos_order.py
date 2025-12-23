# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PosOrder(models.Model):
    _inherit = 'pos.order'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        related='session_id.warehouse_id',
        store=True,
        readonly=True,
        help='Warehouse from POS session'
    )

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        related='session_id.analytic_account_id',
        store=True,
        readonly=True,
        help='Analytic account from POS session'
    )

    def _prepare_invoice_vals(self):
        """Add analytic distribution to invoice if created from POS"""
        vals = super(PosOrder, self)._prepare_invoice_vals()

        if self.analytic_account_id:
            # In Odoo 19, use analytic_distribution instead of analytic_account_id
            vals['invoice_line_ids'] = vals.get('invoice_line_ids', [])
            # Add analytic distribution to invoice lines
            for line in vals.get('invoice_line_ids', []):
                if isinstance(line, (list, tuple)) and len(line) >= 3:
                    line_vals = line[2] if len(line) == 3 else line[1]
                    if isinstance(line_vals, dict):
                        line_vals['analytic_distribution'] = {
                            str(self.analytic_account_id.id): 100
                        }

        return vals

    def _create_account_move(self, dt, ref, journal_id):
        """Override to add analytic distribution to move lines"""
        move = super(PosOrder, self)._create_account_move(dt, ref, journal_id)

        if move and self.analytic_account_id:
            # Add analytic distribution to all move lines
            for line in move.line_ids:
                if not line.analytic_distribution:
                    line.analytic_distribution = {
                        str(self.analytic_account_id.id): 100
                    }

        return move