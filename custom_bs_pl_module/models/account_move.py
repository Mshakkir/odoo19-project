# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        help='Warehouse related to this journal entry',
    )

    @api.model_create_multi
    def create(self, vals_list):
        moves = super(AccountMove, self).create(vals_list)
        # ensure analytic propagation for created moves
        moves._propagate_warehouse_analytic_to_lines()
        return moves

    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        # if warehouse changed, propagate analytic to lines
        if 'warehouse_id' in vals:
            self._propagate_warehouse_analytic_to_lines()
        return res

    def action_post(self):
        # before posting, ensure analytic is set on lines (avoid posting without analytic if expected)
        self._propagate_warehouse_analytic_to_lines()
        return super(AccountMove, self).action_post()

    def _propagate_warehouse_analytic_to_lines(self):
        """
        If this move has a warehouse linked to an analytic account,
        set the analytic_account_id on move lines that don't have analytic set.
        This avoids overwriting manually entered analytic_account_id.
        """
        for move in self:
            if not move.warehouse_id:
                continue
            # assume stock.warehouse has 'analytic_account_id' field
            analytic = getattr(move.warehouse_id, 'analytic_account_id', False)
            if not analytic:
                continue

            # Set analytic only on lines that have no analytic assigned
            lines_to_update = move.line_ids.filtered(lambda l: not l.analytic_account_id)
            if lines_to_update:
                lines_to_update.write({'analytic_account_id': analytic.id})








# # -*- coding: utf-8 -*-
# from odoo import models, fields
#
# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#     warehouse_id = fields.Many2one(
#         'stock.warehouse',
#         string='Warehouse',
#         help='Warehouse related to this journal entry',
#     )
