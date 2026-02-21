# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    date_order_formatted = fields.Char(
        string='Order Date',
        compute='_compute_sale_formatted_dates',
        store=False,
    )

    validity_date_formatted = fields.Char(
        string='Expiration',
        compute='_compute_sale_formatted_dates',
        store=False,
    )

    commitment_date_formatted = fields.Char(
        string='Delivery Date',
        compute='_compute_sale_formatted_dates',
        store=False,
    )

    @api.depends('date_order', 'validity_date', 'commitment_date')
    def _compute_sale_formatted_dates(self):
        for order in self:
            order.date_order_formatted = (
                order.date_order.strftime('%d/%m/%Y')
                if order.date_order else ''
            )
            order.validity_date_formatted = (
                order.validity_date.strftime('%d/%m/%Y')
                if order.validity_date else ''
            )
            order.commitment_date_formatted = (
                order.commitment_date.strftime('%d/%m/%Y')
                if order.commitment_date else ''
            )