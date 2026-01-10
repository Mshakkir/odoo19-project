# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        compute='_compute_delivery_info',
        store=True
    )

    delivery_note_number = fields.Char(
        string='Delivery Note Number',
        compute='_compute_delivery_info',
        store=True
    )

    # shipping_ref = fields.Char(
    #     string='Shipping Ref',
    #     compute='_compute_delivery_info',
    #     store=True
    # )
    awb_number = fields.Char(
        string='Shipping Ref #',
        help='Air Waybill Number for shipment tracking',
        compute='_compute_delivery_info',

    )

    @api.depends('invoice_origin')
    def _compute_delivery_info(self):
        """Compute warehouse, delivery note, and shipping ref from delivery orders"""
        for move in self:
            warehouse = False
            delivery_note = ''
            awb_number = ''

            if move.invoice_origin:
                # Search for related delivery orders
                pickings = self.env['stock.picking'].search([
                    ('origin', '=', move.invoice_origin)
                ], order='date_done desc', limit=1)

                if pickings:
                    picking = pickings[0]

                    # Get warehouse from picking location or picking type
                    if picking.location_id and picking.location_id.warehouse_id:
                        warehouse = picking.location_id.warehouse_id
                    elif picking.picking_type_id and picking.picking_type_id.warehouse_id:
                        warehouse = picking.picking_type_id.warehouse_id

                    # Get delivery note (picking name)
                    delivery_note = picking.name or ''

                    # Get shipping reference (use picking reference or name)
                    # Check if carrier_tracking_ref exists before accessing it
                    if hasattr(picking, 'carrier_tracking_ref') and picking.carrier_tracking_ref:
                        shipping_ref = picking.carrier_tracking_ref
                    else:
                        # Use picking reference or name as fallback
                        shipping_ref = picking.origin or picking.name or ''

            move.warehouse_id = warehouse
            move.delivery_note_number = delivery_note
            move.awb_number = awb_number