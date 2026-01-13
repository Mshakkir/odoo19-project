# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        compute='_compute_warehouse_id',
        store=True
    )

    @api.depends('invoice_origin', 'line_ids.sale_line_ids.order_id.warehouse_id')
    def _compute_warehouse_id(self):
        for move in self:
            warehouse = False
            # Try to get warehouse from sale order via invoice_origin
            if move.invoice_origin:
                sale_order = self.env['sale.order'].search([
                    ('name', '=', move.invoice_origin)
                ], limit=1)
                if sale_order:
                    warehouse = sale_order.warehouse_id

            # If not found, try through invoice lines
            if not warehouse and move.line_ids:
                sale_lines = move.line_ids.mapped('sale_line_ids')
                if sale_lines:
                    warehouse = sale_lines[0].order_id.warehouse_id

            move.warehouse_id = warehouse