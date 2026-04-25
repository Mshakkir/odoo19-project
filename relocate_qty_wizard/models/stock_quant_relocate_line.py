# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockQuantRelocateLine(models.TransientModel):
    _name = 'stock.quant.relocate.line'
    _description = 'Relocate Wizard - Product Quantity Line'

    wizard_id = fields.Many2one(
        'stock.quant.relocate', required=True, ondelete='cascade'
    )
    quant_id = fields.Many2one('stock.quant', required=False, ondelete='set null')
    product_id = fields.Many2one(
        related='quant_id.product_id', string='Product', readonly=True
    )
    available_qty = fields.Float(
        related='quant_id.quantity', string='On Hand', readonly=True
    )
    qty = fields.Float(
        string='Quantity', required=True,
        digits='Product Unit of Measure'
    )

    @api.constrains('qty', 'available_qty')
    def _check_qty(self):
        for line in self:
            if line.qty <= 0:
                raise UserError(
                    _('Quantity must be greater than zero for "%s".')
                    % line.product_id.display_name
                )
            if line.qty > line.available_qty:
                raise UserError(_(
                    'Qty to relocate (%(qty)s) exceeds on-hand (%(avail)s) for "%(product)s".',
                    qty=line.qty,
                    avail=line.available_qty,
                    product=line.product_id.display_name,
                ))
