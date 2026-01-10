# # from odoo import models, fields, api
# #
# #
# # class SaleOrder(models.Model):
# #     _inherit = 'sale.order'
# #
# #     customer_reference = fields.Char(
# #         string='PO Number',
# #         help='PO number or code',
# #         copy=False
# #     )
# #
# #     awb_number = fields.Char(
# #         string='AWB Number',
# #         help='Air Waybill Number',
# #         copy=False
# #     )
# #
# #     @api.onchange('partner_id')
# #     def _onchange_partner_id_custom_fields(self):
# #         """Auto-populate customer reference if partner has default reference"""
# #         if self.partner_id and hasattr(self.partner_id, 'ref'):
# #             self.customer_reference = self.partner_id.ref
# #
# #     def _prepare_invoice(self):
# #         """Override to pass customer reference to invoice"""
# #         invoice_vals = super()._prepare_invoice()
# #         if self.customer_reference:
# #             invoice_vals['customer_reference'] = self.customer_reference
# #         return invoice_vals
#
# from odoo import models, fields, api
#
#
# class SaleOrder(models.Model):
#     _inherit = 'sale.order'
#
#     ref = fields.Char(
#         string='PO Number ',
#         help='PO Number number or code',
#         copy=False
#     )
#
#     awb_number = fields.Char(
#         string='Shipping Ref #',
#         help='Air Waybill Number',
#         copy=False
#     )
#
#     @api.onchange('partner_id')
#     def _onchange_partner_id_custom_fields(self):
#         """Auto-populate customer reference if partner has default reference"""
#         if self.partner_id and hasattr(self.partner_id, 'ref'):
#             self.client_order_ref = self.partner_id.ref
#
#     def _prepare_invoice(self):
#         """Override to pass customer reference and AWB to invoice"""
#         invoice_vals = super()._prepare_invoice()
#         if self.client_order_ref:
#             invoice_vals['customer_reference'] = self.client_order_ref
#         if self.awb_number:
#             invoice_vals['awb_number'] = self.awb_number
#         return invoice_vals

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    ref = fields.Char(
        string='PO Number',
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
        """Override to pass customer reference, AWB, and delivery note to invoice"""
        invoice_vals = super()._prepare_invoice()

        # Transfer PO Number (ref)
        if self.client_order_ref:
            invoice_vals['ref'] = self.client_order_ref

        # Transfer AWB Number
        if self.awb_number:
            invoice_vals['awb_number'] = self.awb_number

        # Transfer Delivery Note Number from completed delivery orders
        pickings = self.picking_ids.filtered(
            lambda p: p.state == 'done' and
                      p.picking_type_code == 'outgoing' and
                      p.delivery_note_number
        )
        if pickings:
            # Get the first delivery with a delivery note number
            invoice_vals['delivery_note_number'] = pickings[0].delivery_note_number

        return invoice_vals