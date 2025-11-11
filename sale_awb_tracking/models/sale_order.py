# -*- coding: utf-8 -*-
from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    awb_number = fields.Char(
        string='AWB Number',
        help='Air Waybill Number for shipment tracking',
        copy=False,
        tracking=True
    )

    def _prepare_invoice(self):
        """Override to include AWB in invoice"""
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        if self.awb_number:
            invoice_vals['awb_number'] = self.awb_number
        return invoice_vals