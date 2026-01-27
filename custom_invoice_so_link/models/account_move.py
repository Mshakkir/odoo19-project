# from odoo import models, fields, api
#
#
# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#     sale_order_id = fields.Many2one(
#         'sale.order',
#         string='Sales Order',
#         domain="[('partner_id', '=', partner_id), ('invoice_status', 'in', ['to invoice', 'invoiced'])]",
#         help="Link this invoice to a specific sales order"
#     )
#
#     delivery_picking_ids = fields.Many2many(
#         'stock.picking',
#         string='Delivery Notes',
#         domain="[('partner_id', '=', partner_id), ('state', '=', 'done'), ('picking_type_code', '=', 'outgoing')]",
#         help="Link this invoice to delivery notes"
#     )
#
#     @api.onchange('partner_id')
#     def _onchange_partner_id_clear_sale_order(self):
#         """Clear sale order when partner changes"""
#         if self.partner_id:
#             self.sale_order_id = False
#             self.delivery_picking_ids = False
#
#     @api.onchange('sale_order_id')
#     def _onchange_sale_order_id(self):
#         """Populate invoice lines from selected sale order"""
#         if self.sale_order_id and self.move_type in ['out_invoice', 'out_refund']:
#             # Create invoice lines from sale order lines
#             invoice_lines = []
#             for line in self.sale_order_id.order_line:
#                 if line.product_id:
#                     invoice_line_vals = {
#                         'product_id': line.product_id.id,
#                         'name': line.name,
#                         'quantity': line.product_uom_qty - line.qty_invoiced,
#                         'price_unit': line.price_unit,
#                         'tax_ids': [(6, 0, line.tax_id.ids)],
#                         'sale_line_ids': [(4, line.id)],
#                     }
#                     invoice_lines.append((0, 0, invoice_line_vals))
#
#             if invoice_lines:
#                 self.invoice_line_ids = invoice_lines

from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        domain="[('partner_id', '=', partner_id), ('invoice_status', 'in', ['to invoice', 'invoiced'])]",
        help="Link this invoice to a specific sales order"
    )

    delivery_picking_ids = fields.Many2many(
        'stock.picking',
        string='Delivery Notes',
        domain="[('partner_id', '=', partner_id), ('state', '=', 'done'), ('picking_type_code', '=', 'outgoing')]",
        help="Link this invoice to delivery notes"
    )

    @api.onchange('partner_id')
    def _onchange_partner_id_clear_sale_order(self):
        """Clear sale order when partner changes"""
        if self.partner_id:
            self.sale_order_id = False
            self.delivery_picking_ids = False

    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        """Populate invoice lines from selected sale order"""
        if self.sale_order_id and self.move_type in ['out_invoice', 'out_refund']:
            invoice_lines = []
            for line in self.sale_order_id.order_line:
                if line.product_id:
                    invoice_line_vals = {
                        'product_id': line.product_id.id,
                        'name': line.name,
                        'quantity': line.product_uom_qty - line.qty_invoiced,
                        'price_unit': line.price_unit,
                        'tax_ids': [(6, 0, line.tax_id.ids)],
                        'sale_line_ids': [(4, line.id)],
                    }
                    invoice_lines.append((0, 0, invoice_line_vals))

            if invoice_lines:
                self.invoice_line_ids = invoice_lines