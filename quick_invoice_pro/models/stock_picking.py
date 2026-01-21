# -*- coding: utf-8 -*-
from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    quick_invoice_delivery = fields.Boolean(
        string='Quick Invoice Delivery',
        help='Created from Quick Invoice module'
    )