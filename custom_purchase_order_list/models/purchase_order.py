# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    amount_tax = fields.Monetary(
        string='Tax Amount',
        store=True,
        readonly=True,
        compute='_compute_amount_tax',
        tracking=True
    )

    @api.depends('amount_total', 'amount_untaxed')
    def _compute_amount_tax(self):
        """Compute tax amount as difference between total and untaxed"""
        for order in self:
            order.amount_tax = order.amount_total - order.amount_untaxed