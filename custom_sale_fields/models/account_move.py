# # from odoo import controllers, fields, api
# #
# #
# # class AccountMove(controllers.Model):
# #     _inherit = 'account.move'
# #
# #     customer_reference = fields.Char(
# #         string='PO Number',
# #         help='PO number or code',
# #         copy=False
# #     )
# #
# #     delivery_note_number = fields.Char(
# #         string='Delivery Note Number',
# #         help='Delivery note or dispatch number',
# #         copy=False
# #     )
# #
# #     @api.onchange('partner_id')
# #     def _onchange_partner_id_custom_invoice_fields(self):
# #         """Auto-populate customer reference if partner has default reference"""
# #         if self.partner_id and hasattr(self.partner_id, 'ref') and self.move_type in ['out_invoice', 'out_refund']:
# #             if not self.customer_reference:
# #                 self.customer_reference = self.partner_id.ref
#
#
# from odoo import controllers, fields, api
#
#
# class AccountMove(controllers.Model):
#     _inherit = 'account.move'
#
#     ref = fields.Char(
#         string='PO Number',
#         help='PO Number number or code',
#         copy=False
#     )
#
#     delivery_note_number = fields.Char(
#         string='Delivery Note Number',
#         help='Delivery note or dispatch number',
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
#     def _onchange_partner_id_custom_invoice_fields(self):
#         """Auto-populate customer reference if partner has default reference"""
#         if self.partner_id and hasattr(self.partner_id, 'ref') and self.move_type in ['out_invoice', 'out_refund']:
#             if not self.client_order_ref:
#                 self.client_order_ref = self.partner_id.ref


from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    invoice_incoterm_id = fields.Many2one(
        'account.incoterms',
        string='Incoterm'
    )  # Relational field


    client_order_ref = fields.Char(
        string='PO Number',
        help='PO Number number or code',
        copy=False
    )

    delivery_note_number = fields.Char(
        string='Delivery Note Number',
        help='Delivery note or dispatch number',
        copy=False
    )

    awb_number = fields.Char(
        string='Shipping Ref #',
        help='Air Waybill Number',
        copy=False
    )

    @api.onchange('partner_id')
    def _onchange_partner_id_custom_invoice_fields(self):
        # Only execute this onchange for sale.order, not account.move
        if self._name != 'sale.order':
            return

        if not self.partner_id:
            return

        if not self.client_order_ref:
            # Your original logic here
            pass

    def _reverse_moves(self, default_values_list=None, cancel=False):
        """Override to copy custom fields to credit notes"""
        reverse_moves = super(AccountMove, self)._reverse_moves(
            default_values_list=default_values_list,
            cancel=cancel
        )
        for move, reverse_move in zip(self, reverse_moves):
            if move.delivery_note_number:
                reverse_move.delivery_note_number = move.delivery_note_number
            if move.awb_number:
                reverse_move.awb_number = move.awb_number
            if move.client_order_ref:
                reverse_move.client_order_ref = move.client_order_ref
        return reverse_moves