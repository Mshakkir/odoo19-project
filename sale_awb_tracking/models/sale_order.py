# # -*- coding: utf-8 -*-
# from odoo import models, fields
#
#
# class SaleOrder(models.Model):
#     _inherit = 'sale.order'
#
#     awb_number = fields.Char(
#         string='AWB Number',
#         help='Air Waybill Number for shipment tracking',
#         copy=False,
#         tracking=True
#     )
#
#     def _prepare_invoice(self):
#         """Override to include AWB in invoice"""
#         invoice_vals = super(SaleOrder, self)._prepare_invoice()
#         if self.awb_number:
#             invoice_vals['awb_number'] = self.awb_number
#         return invoice_vals

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

    def action_confirm(self):
        """Override to include AWB in delivery orders"""
        result = super(SaleOrder, self).action_confirm()
        # Transfer AWB to all pickings created from this sale order
        if self.awb_number:
            for picking in self.picking_ids:
                picking.awb_number = self.awb_number
        return result

