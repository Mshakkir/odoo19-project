# -*- coding: utf-8 -*-
from odoo import fields, models


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Analytic Account',
        help=(
            'Select the analytic account that will be automatically applied '
            'to all vendor bills and journal entries created by users whose '
            'default warehouse is this warehouse.'
        ),
        tracking=True,
    )
