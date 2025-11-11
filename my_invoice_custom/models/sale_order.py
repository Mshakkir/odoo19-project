# -*- coding: utf-8 -*-
from odoo import api, fields, models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    shipping_to = fields.Text(string="Shipping To", help="Enter the shipping address or destination details")
