
# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        compute='_compute_warehouse_id',
        store=True,
        readonly=False,  # Allow manual editing
        precompute=True,
        tracking=True
    )

    @api.depends('invoice_origin', 'line_ids.sale_line_ids.order_id.warehouse_id')
    def _compute_warehouse_id(self):
        for move in self:
            # Skip if warehouse is already manually set
            if move.warehouse_id:
                continue

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

            # If still no warehouse, set default warehouse
            if not warehouse:
                warehouse = self.env['stock.warehouse'].search([
                    ('company_id', '=', move.company_id.id)
                ], limit=1)

            move.warehouse_id = warehouse