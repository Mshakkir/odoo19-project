# -*- coding: utf-8 -*-
from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    awb_number = fields.Char(
        string='Shipping Ref #',
        help='Air Waybill Number for shipment tracking',
        copy=False,
        tracking=True
    )