# -*- coding: utf-8 -*-

from odoo import models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _stock_account_prepare_anglo_saxon_out_lines_vals(self):
        """Override to add analytic account to journal entries from POS"""
        lines_vals_list = super()._stock_account_prepare_anglo_saxon_out_lines_vals()

        # Check if this move is from a POS order
        pos_order = self.env['pos.order'].search([('account_move', '=', self.id)], limit=1)

        if pos_order and pos_order.analytic_account_id:
            # Add analytic distribution to all lines
            for line_vals in lines_vals_list:
                line_vals['analytic_distribution'] = {
                    str(pos_order.analytic_account_id.id): 100
                }

        return lines_vals_list


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        """Add analytic account to move lines created from POS"""
        lines = super(AccountMoveLine, self).create(vals_list)

        for line in lines:
            # If this line is from a POS-related move, add analytic distribution
            if line.move_id and not line.analytic_distribution:
                pos_order = self.env['pos.order'].search([
                    ('account_move', '=', line.move_id.id)
                ], limit=1)

                if pos_order and pos_order.analytic_account_id:
                    line.analytic_distribution = {
                        str(pos_order.analytic_account_id.id): 100
                    }

        return lines