# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Add warehouse field (computed from PO or GR)
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        compute='_compute_warehouse_id',
        store=True,
        readonly=True
    )

    @api.depends('po_number', 'goods_receipt_number')
    def _compute_warehouse_id(self):
        """Compute warehouse from PO or Goods Receipt"""
        for move in self:
            warehouse = False

            # Try to get warehouse from Goods Receipt first
            if move.goods_receipt_number and move.goods_receipt_number.picking_type_id:
                warehouse = move.goods_receipt_number.picking_type_id.warehouse_id

            # If not found, try from PO
            elif move.po_number and move.po_number.picking_type_id:
                warehouse = move.po_number.picking_type_id.warehouse_id

            move.warehouse_id = warehouse