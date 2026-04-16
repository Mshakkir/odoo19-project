# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    # ─── Extra Journal Entries (Many2many) ───────────────────────────────────
    # This lets you link MORE journal entries beyond the auto-generated one.
    extra_account_move_ids = fields.Many2many(
        comodel_name='account.move',
        relation='stock_landed_cost_account_move_rel',
        column1='landed_cost_id',
        column2='move_id',
        string='Extra Journal Entries',
        domain=[('move_type', '=', 'entry')],
        help="Additional journal entries linked to this landed cost.",
    )

    # ─── All Journal Entries (computed) ──────────────────────────────────────
    # Combines the auto-created entry + any extra ones for the smart button count
    all_account_move_ids = fields.Many2many(
        comodel_name='account.move',
        compute='_compute_all_account_move_ids',
        string='All Journal Entries',
    )

    account_move_count = fields.Integer(
        compute='_compute_all_account_move_ids',
        string='Journal Entries Count',
    )

    # ─── Auto-calculate cost from Extra Journal Entries ───────────────────────
    # When enabled, the total of extra journal entries fills the cost lines
    auto_compute_from_moves = fields.Boolean(
        string='Auto-Compute Cost from Journal Entries',
        default=False,
        help="If enabled, the total debit amount from linked extra journal "
             "entries will be used to update the cost line amounts.",
    )

    # ─── Computes ─────────────────────────────────────────────────────────────

    @api.depends('account_move_id', 'extra_account_move_ids')
    def _compute_all_account_move_ids(self):
        for rec in self:
            all_moves = rec.extra_account_move_ids
            if rec.account_move_id:
                all_moves = all_moves | rec.account_move_id
            rec.all_account_move_ids = all_moves
            rec.account_move_count = len(all_moves)

    # ─── Auto-calculate amount from journal entries ────────────────────────────

    @api.onchange('extra_account_move_ids', 'auto_compute_from_moves')
    def _onchange_extra_moves_compute_cost(self):
        """
        When auto_compute_from_moves is True and extra journal entries are
        linked, distribute the total debit of those entries equally across
        all cost lines.
        """
        if not self.auto_compute_from_moves:
            return
        if not self.extra_account_move_ids:
            return

        # Sum up total debit from all linked extra journal entry lines
        total_cost = sum(
            self.extra_account_move_ids.mapped('line_ids')
            .filtered(lambda l: l.debit > 0)
            .mapped('debit')
        )

        if total_cost and self.cost_lines:
            # Distribute equally among existing cost lines
            per_line = total_cost / len(self.cost_lines)
            for line in self.cost_lines:
                line.price_unit = per_line

    # ─── Smart Button Action ───────────────────────────────────────────────────

    def action_open_all_journal_entries(self):
        """Open all journal entries related to this landed cost."""
        self.ensure_one()
        move_ids = self.all_account_move_ids.ids
        return {
            'name': 'Journal Entries',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', move_ids)],
            'context': {'default_move_type': 'entry'},
        }
