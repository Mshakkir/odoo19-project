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

    # AWB Number Display - Air Waybill or shipping reference
    awb_number_display = fields.Char(
        string='AWB Number',
        compute='_compute_awb_number_display',
        store=True,
        readonly=True,
        help="Air Waybill number from the related stock picking"
    )

    # Goods Receipt Number Display - Delivery note or GR number
    goods_receipt_number_display = fields.Char(
        string='Goods Receipt Number',
        compute='_compute_goods_receipt_number_display',
        store=True,
        readonly=True,
        help="Goods receipt number from the related stock picking"
    )

    # PO Number Display - computed field for list view
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
    def _compute_awb_number_display(self):
        """Compute AWB number from stock picking or existing awb_number field"""
        for move in self:
            awb = False

            # First check if awb_number field exists and has value (from other module)
            if hasattr(move, 'awb_number') and move.awb_number:
                # If awb_number is Many2one, get its name
                if hasattr(move.awb_number, 'name'):
                    awb = move.awb_number.name
                else:
                    awb = str(move.awb_number)

            # If no awb_number, get from stock picking
            if not awb and move.invoice_origin:
                pickings = self.env['stock.picking'].search([
                    ('origin', '=', move.invoice_origin)
                ], limit=1)

                if pickings:
                    # Try to get AWB number from different possible field names
                    if hasattr(pickings, 'awb_number'):
                        if hasattr(pickings.awb_number, 'name'):
                            awb = pickings.awb_number.name
                        else:
                            awb = str(pickings.awb_number) if pickings.awb_number else False
                    elif hasattr(pickings, 'carrier_tracking_ref'):
                        awb = pickings.carrier_tracking_ref
                    elif hasattr(pickings, 'shipping_reference'):
                        awb = pickings.shipping_reference

            move.awb_number_display = awb

    @api.depends('invoice_origin')
    def _compute_goods_receipt_number_display(self):
        """Compute goods receipt number from stock picking or existing goods_receipt_number field"""
        for move in self:
            gr_number = False

            # First check if goods_receipt_number field exists and has value (from other module)
            if hasattr(move, 'goods_receipt_number') and move.goods_receipt_number:
                # If goods_receipt_number is Many2one, get its name
                if hasattr(move.goods_receipt_number, 'name'):
                    gr_number = move.goods_receipt_number.name
                else:
                    gr_number = str(move.goods_receipt_number)

            # If no goods_receipt_number, get from stock picking
            if not gr_number and move.invoice_origin:
                pickings = self.env['stock.picking'].search([
                    ('origin', '=', move.invoice_origin)
                ], limit=1)

                if pickings:
                    # Try to get GR number from different possible field names
                    if hasattr(pickings, 'goods_receipt_number'):
                        if hasattr(pickings.goods_receipt_number, 'name'):
                            gr_number = pickings.goods_receipt_number.name
                        else:
                            gr_number = str(pickings.goods_receipt_number) if pickings.goods_receipt_number else False
                    elif hasattr(pickings, 'delivery_note_number'):
                        gr_number = pickings.delivery_note_number
                    elif hasattr(pickings, 'name'):
                        # Fallback to picking name if no specific GR field
                        gr_number = pickings.name

            move.goods_receipt_number_display = gr_number

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