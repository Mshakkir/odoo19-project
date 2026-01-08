from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    # New fields for vendor bill
    po_number = fields.Many2one(
        'purchase.order',
        string='PO Number',
        domain="[('partner_id', '=', partner_id), ('state', 'in', ['purchase', 'done'])]",
        help='Select Purchase Order'
    )
    goods_receipt_number = fields.Many2one(
        'stock.picking',
        string='Goods Receipt (GR)',
        domain="[('partner_id', '=', partner_id), ('picking_type_id.code', '=', 'incoming'), ('state', '=', 'done')]",
        help='Select Goods Receipt'
    )
    awb_number = fields.Char(
        string='AWB Number',
        help='Air Waybill Number'
    )

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Clear PO and GR fields when vendor changes"""
        res = super(AccountMove, self)._onchange_partner_id()
        if self.move_type in ['in_invoice', 'in_refund']:
            self.po_number = False
            self.goods_receipt_number = False
        return res

    @api.onchange('purchase_vendor_bill_id', 'purchase_id')
    def _onchange_purchase_auto_complete(self):
        """Auto-fill PO Number, GR, and AWB when purchase order is selected via Auto-Complete"""
        res = super(AccountMove, self)._onchange_purchase_auto_complete()

        if self.purchase_vendor_bill_id and self.purchase_vendor_bill_id.purchase_order_id:
            po = self.purchase_vendor_bill_id.purchase_order_id

            # Auto-fill PO Number
            self.po_number = po.id

            # Find related Goods Receipt (incoming picking)
            pickings = self.env['stock.picking'].search([
                ('purchase_id', '=', po.id),
                ('picking_type_id.code', '=', 'incoming'),
                ('state', '=', 'done')
            ], limit=1)

            if pickings:
                self.goods_receipt_number = pickings.id

                # Try to get AWB from picking (if stored in carrier_tracking_ref or origin)
                if pickings.carrier_tracking_ref:
                    self.awb_number = pickings.carrier_tracking_ref
                elif not self.awb_number and po.name:
                    # Alternative: you can set a default or leave blank
                    pass

        elif self.purchase_id:
            # Direct purchase_id field (alternative auto-complete method)
            po = self.purchase_id
            self.po_number = po.id

            pickings = self.env['stock.picking'].search([
                ('purchase_id', '=', po.id),
                ('picking_type_id.code', '=', 'incoming'),
                ('state', '=', 'done')
            ], limit=1)

            if pickings:
                self.goods_receipt_number = pickings.id
                if pickings.carrier_tracking_ref:
                    self.awb_number = pickings.carrier_tracking_ref

        return res

    @api.onchange('po_number')
    def _onchange_po_number(self):
        """Populate invoice details when PO is manually selected"""
        if self.po_number:
            po = self.po_number

            # Update bill reference
            if not self.ref:
                self.ref = po.name

            # Set invoice date if not set
            if not self.invoice_date:
                self.invoice_date = fields.Date.today()

            # Find related Goods Receipt
            pickings = self.env['stock.picking'].search([
                ('purchase_id', '=', po.id),
                ('picking_type_id.code', '=', 'incoming'),
                ('state', '=', 'done')
            ], limit=1)

            if pickings:
                self.goods_receipt_number = pickings.id
                if pickings.carrier_tracking_ref:
                    self.awb_number = pickings.carrier_tracking_ref

            # Populate invoice lines from PO if no lines exist
            if not self.invoice_line_ids:
                lines_data = []
                for line in po.order_line:
                    if line.product_id:
                        # Get the correct account based on product
                        account = line.product_id.property_account_expense_id or \
                                  line.product_id.categ_id.property_account_expense_categ_id

                        lines_data.append((0, 0, {
                            'product_id': line.product_id.id,
                            'quantity': line.product_qty - line.qty_invoiced,
                            'price_unit': line.price_unit,
                            'name': line.name,
                            'account_id': account.id if account else False,
                            'tax_ids': [(6, 0, line.taxes_id.ids)],
                            'purchase_line_id': line.id,
                        }))
                if lines_data:
                    self.invoice_line_ids = lines_data

    @api.onchange('goods_receipt_number')
    def _onchange_goods_receipt(self):
        """Update AWB when GR is selected"""
        if self.goods_receipt_number:
            gr = self.goods_receipt_number

            # Auto-populate AWB if available in GR
            if gr.carrier_tracking_ref and not self.awb_number:
                self.awb_number = gr.carrier_tracking_ref

            # If PO is not set, try to set it from GR
            if not self.po_number and gr.purchase_id:
                self.po_number = gr.purchase_id.id









# from odoo import models, fields, api
# from odoo.addons.purchase.models.purchase_order import PurchaseOrder
#
#
# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#     # New fields for vendor bill
#     po_number = fields.Many2one(
#         'purchase.order',
#         string='PO Number',
#         domain="[('partner_id', '=', partner_id), ('state', 'in', ['purchase', 'done'])]",
#         help='Select Purchase Order'
#     )
#     goods_receipt_number = fields.Many2one(
#         'stock.picking',
#         string='Goods Receipt (Delivery In)',
#         domain="[('partner_id', '=', partner_id), ('picking_type_id.code', '=', 'incoming')]",
#         help='Select Goods Receipt'
#     )
#     awb_number = fields.Char(
#         string='AWB Number',
#         help='Air Waybill Number'
#     )
#
#     @api.onchange('partner_id')
#     def onchange_partner_id_custom(self):
#         """Update available PO when vendor is selected"""
#         if self.partner_id and self.move_type in ['in_invoice', 'in_refund']:
#             # Filter PO and GR based on selected vendor
#             pass
#
#     @api.onchange('po_number')
#     def onchange_po_number(self):
#         """Populate PO details when PO is selected"""
#         if self.po_number:
#             po = self.po_number
#             # Show PO details
#             self.ref = f"PO: {po.name}"
#             if not self.invoice_date:
#                 self.invoice_date = fields.Date.today()
#
#             # Optionally populate invoice lines from PO lines
#             if not self.invoice_line_ids:
#                 lines_data = []
#                 for line in po.order_line:
#                     lines_data.append((0, 0, {
#                         'product_id': line.product_id.id,
#                         'quantity': line.product_qty,
#                         'price_unit': line.price_unit,
#                         'name': line.name,
#                     }))
#                 self.invoice_line_ids = lines_data
#
#     @api.onchange('goods_receipt_number')
#     def onchange_goods_receipt(self):
#         """Show GR details"""
#         if self.goods_receipt_number:
#             gr = self.goods_receipt_number
#             if not self.awb_number:
#                 # You can auto-populate AWB if it's stored in GR
#                 pass
#
#     def get_vendor_po_numbers(self):
#         """Get all unpaid PO numbers for selected vendor"""
#         return self.env['purchase.order'].search([
#             ('partner_id', '=', self.partner_id.id),
#             ('state', 'in', ['purchase', 'done']),
#         ])
#
#     def get_vendor_goods_receipts(self):
#         """Get all goods receipts for selected vendor"""
#         return self.env['stock.picking'].search([
#             ('partner_id', '=', self.partner_id.id),
#             ('picking_type_id.code', '=', 'incoming'),
#             ('state', '=', 'done'),
#         ])