# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Default Warehouse',
        help='Default warehouse for new sessions. Can be changed per session.'
    )

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Default Analytic Account',
        help='Default analytic account for this POS. Can be changed per session.'
    )

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        """Auto-populate analytic account based on warehouse name"""
        if self.warehouse_id:
            # Search for analytic account with same name as warehouse
            analytic = self.env['account.analytic.account'].search([
                ('name', '=', self.warehouse_id.name)
            ], limit=1)

            if analytic:
                self.analytic_account_id = analytic.id