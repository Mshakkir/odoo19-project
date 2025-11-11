# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    awb_number = fields.Char(
        string='AWB Number',
        help='Air Waybill Number for shipment tracking',
        copy=False,
        tracking=True
    )