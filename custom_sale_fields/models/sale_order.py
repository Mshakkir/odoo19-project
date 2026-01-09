# from odoo import models, fields, api
#
#
# class SaleOrder(models.Model):
#     _inherit = 'sale.order'
#
#     customer_reference = fields.Char(
#         string='PO Number',
#         help='PO number or code',
#         copy=False
#     )
#
#     awb_number = fields.Char(
#         string='AWB Number',
#         help='Air Waybill Number',
#         copy=False
#     )
#
#     @api.onchange('partner_id')
#     def _onchange_partner_id_custom_fields(self):
#         """Auto-populate customer reference if partner has default reference"""
#         if self.partner_id and hasattr(self.partner_id, 'ref'):
#             self.customer_reference = self.partner_id.ref
#
#     def _prepare_invoice(self):
#         """Override to pass customer reference to invoice"""
#         invoice_vals = super()._prepare_invoice()
#         if self.customer_reference:
#             invoice_vals['customer_reference'] = self.customer_reference
#         return invoice_vals

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    client_order_ref = fields.Char(
        string='PO Number ',
        help='PO Number number or code',
        copy=False
    )

    awb_number = fields.Char(
        string='Shipping Ref #',
        help='Air Waybill Number',
        copy=False
    )

    @api.onchange('partner_id')
    def _onchange_partner_id_custom_fields(self):
        """Auto-populate customer reference if partner has default reference"""
        if self.partner_id and hasattr(self.partner_id, 'ref'):
            self.client_order_ref = self.partner_id.ref

    def _prepare_invoice(self):
        """Override to pass customer reference and AWB to invoice"""
        invoice_vals = super()._prepare_invoice()
        if self.client_order_ref:
            invoice_vals['customer_reference'] = self.client_order_ref
        if self.awb_number:
            invoice_vals['awb_number'] = self.awb_number
        return invoice_vals