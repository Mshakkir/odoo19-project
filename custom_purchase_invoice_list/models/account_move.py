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

    @api.depends('invoice_origin', 'move_type')
    def _compute_warehouse_id(self):
        """Compute warehouse from purchase order for vendor bills"""
        for move in self:
            warehouse = False
            if move.move_type in ('in_invoice', 'in_refund') and move.invoice_origin:
                # Try to get warehouse from purchase order
                purchase_order = self.env['purchase.order'].search([
                    ('name', '=', move.invoice_origin)
                ], limit=1)
                if purchase_order and purchase_order.picking_type_id:
                    warehouse = purchase_order.picking_type_id.warehouse_id

                # If not found, try from stock picking
                if not warehouse:
                    picking = self.env['stock.picking'].search([
                        ('origin', '=', move.invoice_origin)
                    ], limit=1)
                    if picking and picking.picking_type_id:
                        warehouse = picking.picking_type_id.warehouse_id

            move.warehouse_id = warehouse

    @api.depends('invoice_origin', 'move_type')
    def _compute_delivery_note_number(self):
        """Compute delivery note number from related stock picking (receipt)"""
        for move in self:
            delivery_note = False
            if move.move_type in ('in_invoice', 'in_refund') and move.invoice_origin:
                # Search for stock picking related to this invoice
                # First, try direct match with origin
                picking = self.env['stock.picking'].search([
                    ('origin', '=', move.invoice_origin),
                    ('picking_type_code', '=', 'incoming')  # Receipts only
                ], limit=1)

                # If not found, try to find through purchase order
                if not picking:
                    purchase_order = self.env['purchase.order'].search([
                        ('name', '=', move.invoice_origin)
                    ], limit=1)
                    if purchase_order:
                        picking = self.env['stock.picking'].search([
                            ('origin', '=', purchase_order.name),
                            ('picking_type_code', '=', 'incoming')
                        ], limit=1)

                # Get the picking name (receipt number)
                if picking:
                    delivery_note = picking.name

            move.delivery_note_number = delivery_note

    @api.depends('invoice_origin', 'move_type')
    def _compute_awb_number(self):
        """Compute AWB number from related stock picking (receipt)"""
        for move in self:
            awb = False
            if move.move_type in ('in_invoice', 'in_refund') and move.invoice_origin:
                # Search for stock picking related to this invoice
                picking = self.env['stock.picking'].search([
                    ('origin', '=', move.invoice_origin),
                    ('picking_type_code', '=', 'incoming')
                ], limit=1)

                # If not found, try through purchase order
                if not picking:
                    purchase_order = self.env['purchase.order'].search([
                        ('name', '=', move.invoice_origin)
                    ], limit=1)
                    if purchase_order:
                        picking = self.env['stock.picking'].search([
                            ('origin', '=', purchase_order.name),
                            ('picking_type_code', '=', 'incoming')
                        ], limit=1)

                # Get the carrier tracking ref (AWB number)
                if picking and picking.carrier_tracking_ref:
                    awb = picking.carrier_tracking_ref

            move.awb_number = awb