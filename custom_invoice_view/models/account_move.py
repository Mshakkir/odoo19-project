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

    shipping_ref = fields.Char(
        string='Shipping Ref',
        compute='_compute_delivery_info',
        store=True
    )

    @api.depends('invoice_origin', 'line_ids')
    def _compute_delivery_info(self):
        """Compute warehouse, delivery note, and shipping ref from related documents"""
        for move in self:
            warehouse = False
            delivery_note = ''
            shipping_ref = ''

            if move.invoice_origin:
                # Try to get delivery orders related to this invoice
                pickings = self.env['stock.picking'].search([
                    ('origin', '=', move.invoice_origin),
                    ('state', '=', 'done')
                ], order='date_done desc', limit=1)

                if pickings:
                    # Get warehouse from picking
                    warehouse = pickings.location_id.warehouse_id or pickings.picking_type_id.warehouse_id
                    delivery_note = pickings.name or ''
                    # Shipping ref could be the tracking reference or picking name
                    shipping_ref = pickings.carrier_tracking_ref or pickings.name or ''
                else:
                    # If no delivery, try to get from sale order
                    sale_order = self.env['sale.order'].search([
                        ('name', '=', move.invoice_origin)
                    ], limit=1)

                    if sale_order:
                        # Try to get warehouse from sale order if it has the field
                        if hasattr(sale_order, 'warehouse_id'):
                            warehouse = sale_order.warehouse_id
                        # Alternative: get from picking_ids
                        elif sale_order.picking_ids:
                            first_picking = sale_order.picking_ids[0]
                            warehouse = first_picking.location_id.warehouse_id or first_picking.picking_type_id.warehouse_id

            move.warehouse_id = warehouse
            move.delivery_note_number = delivery_note
            move.shipping_ref = shipping_ref