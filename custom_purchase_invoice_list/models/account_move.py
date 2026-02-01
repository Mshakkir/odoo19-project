# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Warehouse field - computed from purchase order or stock picking
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        compute='_compute_warehouse_id',
        store=True,
        readonly=True,
        help="Warehouse computed from related purchase order or stock picking"
    )

    # Buyer field - the user responsible for the purchase
    buyer_id = fields.Many2one(
        'res.users',
        string='Buyer',
        compute='_compute_buyer_id',
        store=True,
        readonly=True,
        help="Purchase representative from the related purchase order"
    )

    # AWB Number - Air Waybill or shipping reference
    awb_number = fields.Char(
        string='AWB Number',
        compute='_compute_awb_number',
        store=True,
        readonly=True,
        help="Air Waybill number from the related stock picking"
    )

    # Goods Receipt Number - Delivery note or GR number
    goods_receipt_number = fields.Char(
        string='Goods Receipt Number',
        compute='_compute_goods_receipt_number',
        store=True,
        readonly=True,
        help="Goods receipt number from the related stock picking"
    )

    # PO Number Display - computed field for list view
    # Note: po_number already exists as Many2one in another module
    # We create a computed Char field for display purposes
    po_number_display = fields.Char(
        string='PO Number',
        compute='_compute_po_number_display',
        store=True,
        readonly=True,
        help="Purchase Order number(s) from the related purchase order"
    )

    @api.depends('line_ids.purchase_line_id.order_id')
    def _compute_warehouse_id(self):
        """Compute warehouse from purchase order or stock picking"""
        for move in self:
            warehouse = False

            # Try to get warehouse from purchase order lines
            purchase_orders = move.line_ids.mapped('purchase_line_id.order_id')
            if purchase_orders:
                # Take the first PO's warehouse
                warehouse = purchase_orders[0].picking_type_id.warehouse_id

            # If no PO, try to get from stock pickings via invoice_origin
            if not warehouse and move.invoice_origin:
                pickings = self.env['stock.picking'].search([
                    ('origin', '=', move.invoice_origin)
                ], limit=1)
                if pickings:
                    warehouse = pickings.picking_type_id.warehouse_id

            move.warehouse_id = warehouse

    @api.depends('line_ids.purchase_line_id.order_id.user_id')
    def _compute_buyer_id(self):
        """Compute buyer from purchase order"""
        for move in self:
            buyer = False

            # Get buyer from purchase order
            purchase_orders = move.line_ids.mapped('purchase_line_id.order_id')
            if purchase_orders:
                # Take the first PO's user
                buyer = purchase_orders[0].user_id

            move.buyer_id = buyer

    @api.depends('invoice_origin')
    def _compute_awb_number(self):
        """Compute AWB number from stock picking"""
        for move in self:
            awb = False

            if move.invoice_origin:
                # Search for stock picking with matching origin
                pickings = self.env['stock.picking'].search([
                    ('origin', '=', move.invoice_origin)
                ], limit=1)

                if pickings:
                    # Try to get AWB number from different possible field names
                    # Adjust field name based on your actual field in stock.picking
                    if hasattr(pickings, 'awb_number'):
                        awb = pickings.awb_number
                    elif hasattr(pickings, 'carrier_tracking_ref'):
                        awb = pickings.carrier_tracking_ref
                    elif hasattr(pickings, 'shipping_reference'):
                        awb = pickings.shipping_reference

            move.awb_number = awb

    @api.depends('invoice_origin')
    def _compute_goods_receipt_number(self):
        """Compute goods receipt number from stock picking"""
        for move in self:
            gr_number = False

            if move.invoice_origin:
                # Search for stock picking with matching origin
                pickings = self.env['stock.picking'].search([
                    ('origin', '=', move.invoice_origin)
                ], limit=1)

                if pickings:
                    # Try to get GR number from different possible field names
                    # Adjust field name based on your actual field in stock.picking
                    if hasattr(pickings, 'goods_receipt_number'):
                        gr_number = pickings.goods_receipt_number
                    elif hasattr(pickings, 'delivery_note_number'):
                        gr_number = pickings.delivery_note_number
                    elif hasattr(pickings, 'name'):
                        # Fallback to picking name if no specific GR field
                        gr_number = pickings.name

            move.goods_receipt_number = gr_number

    @api.depends('line_ids.purchase_line_id.order_id.name', 'po_number')
    def _compute_po_number_display(self):
        """Compute PO number display from purchase order or existing po_number field"""
        for move in self:
            po_display = False

            # First check if po_number field exists and has value (from other module)
            if hasattr(move, 'po_number') and move.po_number:
                # If po_number is Many2one, get its name
                if hasattr(move.po_number, 'name'):
                    po_display = move.po_number.name
                else:
                    po_display = str(move.po_number)

            # If no po_number, get from purchase order lines
            if not po_display:
                purchase_orders = move.line_ids.mapped('purchase_line_id.order_id')
                if purchase_orders:
                    # Join multiple PO numbers with comma if multiple POs
                    po_numbers = purchase_orders.mapped('name')
                    po_display = ', '.join(po_numbers) if po_numbers else False

            move.po_number_display = po_display