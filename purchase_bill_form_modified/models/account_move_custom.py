from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    # New fields for vendor bill
    po_number = fields.Many2one(
        'purchase.order',
        string='PO Number',
        domain="[('partner_id', '=', partner_id), ('state', 'in', ['purchase', 'done']), ('invoice_status', 'in', ['to invoice', 'no'])]",
        help='Select Purchase Order - Only shows POs waiting for bill'
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
            self.awb_number = False
        return res

    @api.model
    def _get_purchase_orders(self, partner_id):
        """Get unbilled purchase orders for the vendor"""
        return self.env['purchase.order'].search([
            ('partner_id', '=', partner_id),
            ('state', 'in', ['purchase', 'done']),
            ('invoice_status', 'in', ['to invoice', 'no'])
        ])

    @api.onchange('purchase_vendor_bill_id', 'purchase_id')
    def _onchange_purchase_auto_complete(self):
        """Auto-fill PO Number, GR, and AWB when purchase order is selected via Auto-Complete"""
        res = super(AccountMove, self)._onchange_purchase_auto_complete()

        if self.purchase_vendor_bill_id and self.purchase_vendor_bill_id.purchase_order_id:
            po = self.purchase_vendor_bill_id.purchase_order_id

            # Auto-fill PO Number
            self.po_number = po.id

            # Auto-fill AWB from Purchase Order
            if hasattr(po, 'awb_number') and po.awb_number:
                self.awb_number = po.awb_number

            # Find related Goods Receipt (incoming picking)
            pickings = self.env['stock.picking'].search([
                ('purchase_id', '=', po.id),
                ('picking_type_id.code', '=', 'incoming'),
                ('state', '=', 'done')
            ], limit=1)

            if pickings:
                self.goods_receipt_number = pickings.id

        elif self.purchase_id:
            # Direct purchase_id field (alternative auto-complete method)
            po = self.purchase_id
            self.po_number = po.id

            # Auto-fill AWB from Purchase Order
            if hasattr(po, 'awb_number') and po.awb_number:
                self.awb_number = po.awb_number

            pickings = self.env['stock.picking'].search([
                ('purchase_id', '=', po.id),
                ('picking_type_id.code', '=', 'incoming'),
                ('state', '=', 'done')
            ], limit=1)

            if pickings:
                self.goods_receipt_number = pickings.id

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

            # Auto-fill AWB from Purchase Order
            if hasattr(po, 'awb_number') and po.awb_number and not self.awb_number:
                self.awb_number = po.awb_number

            # Find related Goods Receipt
            pickings = self.env['stock.picking'].search([
                ('purchase_id', '=', po.id),
                ('picking_type_id.code', '=', 'incoming'),
                ('state', '=', 'done')
            ], limit=1)

            if pickings:
                self.goods_receipt_number = pickings.id

            # Populate invoice lines from PO if no lines exist
            if not self.invoice_line_ids:
                lines_data = []
                for line in po.order_line:
                    if line.product_id:
                        # Get the correct account based on product
                        account = line.product_id.property_account_expense_id or \
                                  line.product_id.categ_id.property_account_expense_categ_id

                        # Calculate remaining quantity to invoice
                        qty_to_invoice = line.product_qty - line.qty_invoiced

                        if qty_to_invoice > 0:
                            lines_data.append((0, 0, {
                                'product_id': line.product_id.id,
                                'quantity': qty_to_invoice,
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
        """Update PO and AWB when GR is selected"""
        if self.goods_receipt_number:
            gr = self.goods_receipt_number

            # If PO is not set, try to set it from GR
            if not self.po_number and gr.purchase_id:
                self.po_number = gr.purchase_id.id

                # Also get AWB from the related PO
                if hasattr(gr.purchase_id, 'awb_number') and gr.purchase_id.awb_number and not self.awb_number:
                    self.awb_number = gr.purchase_id.awb_number








# from odoo import models, fields, api
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
#         string='Goods Receipt (GR)',
#         domain="[('partner_id', '=', partner_id), ('picking_type_id.code', '=', 'incoming'), ('state', '=', 'done')]",
#         help='Select Goods Receipt'
#     )
#     awb_number = fields.Char(
#         string='AWB Number',
#         help='Air Waybill Number'
#     )
#
#     @api.onchange('partner_id')
#     def _onchange_partner_id(self):
#         """Clear PO and GR fields when vendor changes"""
#         res = super(AccountMove, self)._onchange_partner_id()
#         if self.move_type in ['in_invoice', 'in_refund']:
#             self.po_number = False
#             self.goods_receipt_number = False
#             self.awb_number = False
#         return res
#
#     @api.onchange('purchase_vendor_bill_id', 'purchase_id')
#     def _onchange_purchase_auto_complete(self):
#         """Auto-fill PO Number, GR, and AWB when purchase order is selected via Auto-Complete"""
#         res = super(AccountMove, self)._onchange_purchase_auto_complete()
#
#         if self.purchase_vendor_bill_id and self.purchase_vendor_bill_id.purchase_order_id:
#             po = self.purchase_vendor_bill_id.purchase_order_id
#
#             # Auto-fill PO Number
#             self.po_number = po.id
#
#             # Auto-fill AWB from Purchase Order
#             if hasattr(po, 'awb_number') and po.awb_number:
#                 self.awb_number = po.awb_number
#
#             # Find related Goods Receipt (incoming picking)
#             pickings = self.env['stock.picking'].search([
#                 ('purchase_id', '=', po.id),
#                 ('picking_type_id.code', '=', 'incoming'),
#                 ('state', '=', 'done')
#             ], limit=1)
#
#             if pickings:
#                 self.goods_receipt_number = pickings.id
#
#         elif self.purchase_id:
#             # Direct purchase_id field (alternative auto-complete method)
#             po = self.purchase_id
#             self.po_number = po.id
#
#             # Auto-fill AWB from Purchase Order
#             if hasattr(po, 'awb_number') and po.awb_number:
#                 self.awb_number = po.awb_number
#
#             pickings = self.env['stock.picking'].search([
#                 ('purchase_id', '=', po.id),
#                 ('picking_type_id.code', '=', 'incoming'),
#                 ('state', '=', 'done')
#             ], limit=1)
#
#             if pickings:
#                 self.goods_receipt_number = pickings.id
#
#         return res
#
#     @api.onchange('po_number')
#     def _onchange_po_number(self):
#         """Populate invoice details when PO is manually selected"""
#         if self.po_number:
#             po = self.po_number
#
#             # Update bill reference
#             if not self.ref:
#                 self.ref = po.name
#
#             # Set invoice date if not set
#             if not self.invoice_date:
#                 self.invoice_date = fields.Date.today()
#
#             # Auto-fill AWB from Purchase Order
#             if hasattr(po, 'awb_number') and po.awb_number and not self.awb_number:
#                 self.awb_number = po.awb_number
#
#             # Find related Goods Receipt
#             pickings = self.env['stock.picking'].search([
#                 ('purchase_id', '=', po.id),
#                 ('picking_type_id.code', '=', 'incoming'),
#                 ('state', '=', 'done')
#             ], limit=1)
#
#             if pickings:
#                 self.goods_receipt_number = pickings.id
#
#             # Populate invoice lines from PO if no lines exist
#             if not self.invoice_line_ids:
#                 lines_data = []
#                 for line in po.order_line:
#                     if line.product_id:
#                         # Get the correct account based on product
#                         account = line.product_id.property_account_expense_id or \
#                                   line.product_id.categ_id.property_account_expense_categ_id
#
#                         # Calculate remaining quantity to invoice
#                         qty_to_invoice = line.product_qty - line.qty_invoiced
#
#                         if qty_to_invoice > 0:
#                             lines_data.append((0, 0, {
#                                 'product_id': line.product_id.id,
#                                 'quantity': qty_to_invoice,
#                                 'price_unit': line.price_unit,
#                                 'name': line.name,
#                                 'account_id': account.id if account else False,
#                                 'tax_ids': [(6, 0, line.taxes_id.ids)],
#                                 'purchase_line_id': line.id,
#                             }))
#                 if lines_data:
#                     self.invoice_line_ids = lines_data
#
#     @api.onchange('goods_receipt_number')
#     def _onchange_goods_receipt(self):
#         """Update PO and AWB when GR is selected"""
#         if self.goods_receipt_number:
#             gr = self.goods_receipt_number
#
#             # If PO is not set, try to set it from GR
#             if not self.po_number and gr.purchase_id:
#                 self.po_number = gr.purchase_id.id
#
#                 # Also get AWB from the related PO
#                 if hasattr(gr.purchase_id, 'awb_number') and gr.purchase_id.awb_number and not self.awb_number:
#                     self.awb_number = gr.purchase_id.awb_number
