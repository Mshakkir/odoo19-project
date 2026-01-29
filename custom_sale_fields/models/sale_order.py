# # # from odoo import controllers, fields, api
# # #
# # #
# # # class SaleOrder(controllers.Model):
# # #     _inherit = 'sale.order'
# # #
# # #     customer_reference = fields.Char(
# # #         string='PO Number',
# # #         help='PO number or code',
# # #         copy=False
# # #     )
# # #
# # #     awb_number = fields.Char(
# # #         string='AWB Number',
# # #         help='Air Waybill Number',
# # #         copy=False
# # #     )
# # #
# # #     @api.onchange('partner_id')
# # #     def _onchange_partner_id_custom_fields(self):
# # #         """Auto-populate customer reference if partner has default reference"""
# # #         if self.partner_id and hasattr(self.partner_id, 'ref'):
# # #             self.customer_reference = self.partner_id.ref
# # #
# # #     def _prepare_invoice(self):
# # #         """Override to pass customer reference to invoice"""
# # #         invoice_vals = super()._prepare_invoice()
# # #         if self.customer_reference:
# # #             invoice_vals['customer_reference'] = self.customer_reference
# # #         return invoice_vals
# #
# # from odoo import controllers, fields, api
# #
# #
# # class SaleOrder(controllers.Model):
# #     _inherit = 'sale.order'
# #
# #     ref = fields.Char(
# #         string='PO Number ',
# #         help='PO Number number or code',
# #         copy=False
# #     )
# #
# #     awb_number = fields.Char(
# #         string='Shipping Ref #',
# #         help='Air Waybill Number',
# #         copy=False
# #     )
# #
# #     @api.onchange('partner_id')
# #     def _onchange_partner_id_custom_fields(self):
# #         """Auto-populate customer reference if partner has default reference"""
# #         if self.partner_id and hasattr(self.partner_id, 'ref'):
# #             self.client_order_ref = self.partner_id.ref
# #
# #     def _prepare_invoice(self):
# #         """Override to pass customer reference and AWB to invoice"""
# #         invoice_vals = super()._prepare_invoice()
# #         if self.client_order_ref:
# #             invoice_vals['customer_reference'] = self.client_order_ref
# #         if self.awb_number:
# #             invoice_vals['awb_number'] = self.awb_number
# #         return invoice_vals
#
# from odoo import controllers, fields, api
#
#
# class SaleOrder(controllers.Model):
#     _inherit = 'sale.order'
#
#     ref = fields.Char(
#         string='PO Number',
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
#         """Override to pass PO Number, AWB, and delivery note to invoice"""
#         invoice_vals = super()._prepare_invoice()
#
#         # Transfer PO Number (ref) - from Sale Order's client_order_ref OR ref field
#         if self.client_order_ref:
#             invoice_vals['ref'] = self.client_order_ref
#         elif self.ref:
#             invoice_vals['ref'] = self.ref
#
#         # Transfer AWB Number from Sale Order
#         if self.awb_number:
#             invoice_vals['awb_number'] = self.awb_number
#
#         # Transfer Delivery Note Number from completed delivery orders
#         # Check if there are any completed delivery orders
#         completed_pickings = self.picking_ids.filtered(
#             lambda p: p.state == 'done' and p.picking_type_code == 'outgoing'
#         )
#
#         if completed_pickings:
#             # Get delivery note from the first completed delivery
#             for picking in completed_pickings:
#                 if picking.delivery_note_number:
#                     invoice_vals['delivery_note_number'] = picking.delivery_note_number
#                     break
#
#             # Get AWB from delivery if not set on sale order
#             if not self.awb_number:
#                 for picking in completed_pickings:
#                     if picking.awb_number:
#                         invoice_vals['awb_number'] = picking.awb_number
#                         break
#
#         return invoice_vals
#
#     def action_confirm(self):
#         """Copy AWB number to delivery orders when sale order is confirmed"""
#         result = super().action_confirm()
#
#         # Transfer AWB to delivery orders
#         if self.awb_number:
#             for picking in self.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing'):
#                 if not picking.awb_number:
#                     picking.awb_number = self.awb_number
#
#         return result

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
        """Override to pass PO Number, AWB, and delivery note to invoice"""
        invoice_vals = super()._prepare_invoice()

        # Transfer PO Number (ref) - from Sale Order's client_order_ref OR ref field
        if self.client_order_ref:
            invoice_vals['ref'] = self.client_order_ref
        elif self.ref:
            invoice_vals['ref'] = self.ref

        # Transfer AWB Number from Sale Order
        if self.awb_number:
            invoice_vals['awb_number'] = self.awb_number

        # Auto-populate Delivery Note Number from completed delivery orders
        completed_pickings = self.picking_ids.filtered(
            lambda p: p.state == 'done' and p.picking_type_code == 'outgoing'
        )

        if completed_pickings:
            # Use the delivery order NAME (reference) as the delivery note number
            # If there's a custom delivery_note_number field, use that, otherwise use the name
            delivery_note_numbers = []

            for picking in completed_pickings:
                # Priority 1: Custom delivery note number (if manually entered)
                if hasattr(picking, 'delivery_note_number') and picking.delivery_note_number:
                    delivery_note_numbers.append(picking.delivery_note_number)
                # Priority 2: Use the delivery order reference (MAIN/OUT/00029)
                elif picking.name:
                    delivery_note_numbers.append(picking.name)

            # Join multiple delivery notes with comma if there are multiple deliveries
            if delivery_note_numbers:
                invoice_vals['delivery_note_number'] = ', '.join(delivery_note_numbers)

            # Get AWB from delivery if not set on sale order
            if not self.awb_number:
                for picking in completed_pickings:
                    if hasattr(picking, 'awb_number') and picking.awb_number:
                        invoice_vals['awb_number'] = picking.awb_number
                        break

        return invoice_vals

    def action_confirm(self):
        """Copy AWB number to delivery orders when sale order is confirmed"""
        result = super().action_confirm()

        # Transfer AWB to delivery orders
        if self.awb_number:
            for picking in self.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing'):
                if not picking.awb_number:
                    picking.awb_number = self.awb_number

        return result