# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        compute='_compute_warehouse_id',
        store=True,
        readonly=True
    )

    delivery_note_number = fields.Char(
        string='Delivery Note Number',
        compute='_compute_delivery_note_number',
        store=True,
        readonly=True
    )

    awb_number = fields.Char(
        string='AWB Number',
        compute='_compute_awb_number',
        store=True,
        readonly=True
    )

    @api.depends('invoice_origin', 'move_type', 'line_ids', 'line_ids.purchase_line_id')
    def _compute_warehouse_id(self):
        """Compute warehouse from purchase order for vendor bills"""
        for move in self:
            warehouse = False
            if move.move_type in ('in_invoice', 'in_refund'):
                # Try to get warehouse from purchase order line
                purchase_line = move.line_ids.mapped('purchase_line_id')[:1]
                if purchase_line and purchase_line.order_id.picking_type_id:
                    warehouse = purchase_line.order_id.picking_type_id.warehouse_id

                # If not found and invoice_origin exists, try from purchase order
                if not warehouse and move.invoice_origin:
                    purchase_order = self.env['purchase.order'].search([
                        ('name', '=', move.invoice_origin)
                    ], limit=1)
                    if purchase_order and purchase_order.picking_type_id:
                        warehouse = purchase_order.picking_type_id.warehouse_id

            move.warehouse_id = warehouse

    @api.depends('invoice_origin', 'move_type', 'line_ids', 'line_ids.purchase_line_id')
    def _compute_delivery_note_number(self):
        """Compute delivery note number from related stock picking (receipt)"""
        for move in self:
            delivery_note = False
            if move.move_type in ('in_invoice', 'in_refund'):
                # Method 1: Get from purchase order line -> picking
                purchase_lines = move.line_ids.mapped('purchase_line_id')
                if purchase_lines:
                    # Get pickings from purchase order
                    purchase_order = purchase_lines[0].order_id
                    pickings = self.env['stock.picking'].search([
                        ('purchase_id', '=', purchase_order.id),
                        ('state', '=', 'done'),
                        ('picking_type_code', '=', 'incoming')
                    ], limit=1)
                    if pickings:
                        delivery_note = pickings.name

                # Method 2: Try from invoice origin
                if not delivery_note and move.invoice_origin:
                    # Try direct picking reference
                    picking = self.env['stock.picking'].search([
                        ('name', '=', move.invoice_origin),
                        ('picking_type_code', '=', 'incoming')
                    ], limit=1)
                    if picking:
                        delivery_note = picking.name
                    else:
                        # Try through purchase order
                        purchase_order = self.env['purchase.order'].search([
                            ('name', '=', move.invoice_origin)
                        ], limit=1)
                        if purchase_order:
                            pickings = self.env['stock.picking'].search([
                                ('purchase_id', '=', purchase_order.id),
                                ('state', '=', 'done'),
                                ('picking_type_code', '=', 'incoming')
                            ], limit=1)
                            if pickings:
                                delivery_note = pickings.name

            move.delivery_note_number = delivery_note

    @api.depends('invoice_origin', 'move_type', 'line_ids', 'line_ids.purchase_line_id')
    def _compute_awb_number(self):
        """Compute AWB number from related stock picking (receipt)"""
        for move in self:
            awb = False
            if move.move_type in ('in_invoice', 'in_refund'):
                # Method 1: Get from purchase order line -> picking
                purchase_lines = move.line_ids.mapped('purchase_line_id')
                if purchase_lines:
                    purchase_order = purchase_lines[0].order_id
                    pickings = self.env['stock.picking'].search([
                        ('purchase_id', '=', purchase_order.id),
                        ('state', '=', 'done'),
                        ('picking_type_code', '=', 'incoming')
                    ], limit=1)
                    if pickings and pickings.carrier_tracking_ref:
                        awb = pickings.carrier_tracking_ref

                # Method 2: Try from invoice origin
                if not awb and move.invoice_origin:
                    picking = self.env['stock.picking'].search([
                        ('name', '=', move.invoice_origin),
                        ('picking_type_code', '=', 'incoming')
                    ], limit=1)
                    if picking and picking.carrier_tracking_ref:
                        awb = picking.carrier_tracking_ref
                    else:
                        purchase_order = self.env['purchase.order'].search([
                            ('name', '=', move.invoice_origin)
                        ], limit=1)
                        if purchase_order:
                            pickings = self.env['stock.picking'].search([
                                ('purchase_id', '=', purchase_order.id),
                                ('state', '=', 'done'),
                                ('picking_type_code', '=', 'incoming')
                            ], limit=1)
                            if pickings and pickings.carrier_tracking_ref:
                                awb = pickings.carrier_tracking_ref

            move.awb_number = awb