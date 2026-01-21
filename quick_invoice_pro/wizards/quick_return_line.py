# -*- coding: utf-8 -*-
from odoo import models, fields, api

class QuickReturnLine(models.TransientModel):
    _name = 'quick.return.line'
    _description = 'Quick Return Line'

    wizard_id = fields.Many2one(
        'quick.return.wizard',
        required=True,
        ondelete='cascade'
    )

    product_id = fields.Many2one(
        'product.product',
        readonly=True
    )

    ordered_qty = fields.Float(readonly=True)
    return_qty = fields.Float(required=True)
    price_unit = fields.Float(readonly=True)

    subtotal = fields.Float(
        compute='_compute_subtotal',
        store=True
    )

    @api.depends('return_qty', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.return_qty * line.price_unit
