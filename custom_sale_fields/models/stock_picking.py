# -*- coding: utf-8 -*-
from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    delivery_note_number = fields.Char(
        string='Delivery Note #',
        help='Delivery note or dispatch number',
        copy=False,
        tracking=True
    )

    awb_number = fields.Char(
        string='Shipping Ref #',
        help='Air Waybill Number / Shipping Reference',
        copy=False,
        tracking=True
    )