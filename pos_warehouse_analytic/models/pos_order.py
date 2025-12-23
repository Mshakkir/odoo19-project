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
        """Add analytic account to invoice if created from POS"""
        vals = super(PosOrder, self)._prepare_invoice_vals()

        if self.analytic_account_id:
            vals['analytic_account_id'] = self.analytic_account_id.id

        return vals