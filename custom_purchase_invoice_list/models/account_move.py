# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        compute='_compute_warehouse_and_delivery',
        store=True,
        readonly=True
    )

    delivery_note_number = fields.Char(
        string='Delivery Note Number',
        compute='_compute_warehouse_and_delivery',
        store=True,
        readonly=True
    )

    awb_number = fields.Char(
        string='AWB Number',
        compute='_compute_warehouse_and_delivery',
        store=True,
        readonly=True
    )

    @api.depends('invoice_origin', 'move_type', 'ref')
    def _compute_warehouse_and_delivery(self):
        """Compute warehouse, delivery note, and AWB from related records"""
        for move in self:
            warehouse = False
            delivery_note = False
            awb = False

            if move.move_type in ('in_invoice', 'in_refund'):
                picking = False
                purchase_order = False

                # Method 1: Try to find picking by name in ref or invoice_origin
                if move.ref:
                    picking = self.env['stock.picking'].search([
                        ('name', '=', move.ref),
                        ('picking_type_code', '=', 'incoming')
                    ], limit=1)

                # Method 2: Try invoice_origin for picking
                if not picking and move.invoice_origin:
                    picking = self.env['stock.picking'].search([
                        ('name', '=', move.invoice_origin),
                        ('picking_type_code', '=', 'incoming')
                    ], limit=1)

                # Method 3: Get purchase order from invoice_origin
                if move.invoice_origin and not picking:
                    # Try to find PO
                    purchase_order = self.env['purchase.order'].search([
                        ('name', '=', move.invoice_origin)
                    ], limit=1)

                    if purchase_order:
                        # Get related pickings
                        picking = self.env['stock.picking'].search([
                            ('origin', '=', purchase_order.name),
                            ('picking_type_code', '=', 'incoming'),
                            ('state', '=', 'done')
                        ], order='date_done desc', limit=1)

                        # Also try by purchase_id field if available
                        if not picking:
                            picking = self.env['stock.picking'].search([
                                ('purchase_id', '=', purchase_order.id),
                                ('picking_type_code', '=', 'incoming'),
                                ('state', '=', 'done')
                            ], order='date_done desc', limit=1)

                # Method 4: Get from purchase order lines in invoice
                if not picking and not purchase_order:
                    purchase_lines = move.invoice_line_ids.mapped('purchase_line_id')
                    if purchase_lines:
                        purchase_order = purchase_lines[0].order_id
                        picking = self.env['stock.picking'].search([
                            ('purchase_id', '=', purchase_order.id),
                            ('picking_type_code', '=', 'incoming'),
                            ('state', '=', 'done')
                        ], order='date_done desc', limit=1)

                # Extract data from picking
                if picking:
                    delivery_note = picking.name
                    if picking.carrier_tracking_ref:
                        awb = picking.carrier_tracking_ref
                    if picking.picking_type_id and picking.picking_type_id.warehouse_id:
                        warehouse = picking.picking_type_id.warehouse_id

                # Get warehouse from purchase order if not found from picking
                if not warehouse and purchase_order:
                    if purchase_order.picking_type_id and purchase_order.picking_type_id.warehouse_id:
                        warehouse = purchase_order.picking_type_id.warehouse_id

            move.warehouse_id = warehouse
            move.delivery_note_number = delivery_note
            move.awb_number = awb