# # -*- coding: utf-8 -*-
# from odoo import controllers, fields
#
#
# class StockPicking(controllers.Model):
#     _inherit = 'stock.picking'
#
#     delivery_note_number = fields.Char(
#         string='Delivery Note #',
#         help='Delivery note or dispatch number',
#         copy=False,
#         tracking=True
#     )
#
#     awb_number = fields.Char(
#         string='Shipping Ref #',
#         help='Air Waybill Number / Shipping Reference',
#         copy=False,
#         tracking=True
#     )
# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    delivery_note_number = fields.Char(
        string='Delivery Note #',
        help='Custom delivery note or dispatch number (leave empty to use delivery order reference)',
        copy=False,
        tracking=True
    )

    awb_number = fields.Char(
        string='Shipping Ref #',
        help='Air Waybill Number / Shipping Reference',
        copy=False,
        tracking=True
    )

    @api.model
    def create(self, vals):
        """Auto-populate delivery_note_number with the delivery order name if not provided"""
        picking = super().create(vals)

        # If delivery_note_number is empty and this is an outgoing delivery, use the name
        if not picking.delivery_note_number and picking.picking_type_code == 'outgoing' and picking.name:
            picking.delivery_note_number = picking.name

        return picking