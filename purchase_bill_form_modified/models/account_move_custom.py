# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    # PO Number field
    po_number = fields.Many2one(
        'purchase.order',
        string='PO Number',
        domain="[('partner_id', '=', partner_id), ('state', 'in', ['purchase', 'done'])]",
        help='Select Purchase Order',
        copy=False
    )

    # Goods Receipt field
    goods_receipt_number = fields.Many2one(
        'stock.picking',
        string='Goods Receipt (GR)',
        domain="[('partner_id', '=', partner_id), ('picking_type_id.code', '=', 'incoming'), ('state', '=', 'done')]",
        help='Select Goods Receipt',
        copy=False
    )

    # AWB Number field
    awb_number = fields.Char(
        string='Shipping Ref#',
        help='Air Waybill Number',
        copy=False
    )

    # Warehouse field (from PO - picking_type_id)
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        help='Warehouse from Purchase Order',
        copy=False,
        store=True
    )

    # Buyer field (from PO - user_id)
    buyer_id = fields.Many2one(
        'res.users',
        string='Buyer',
        help='Buyer from Purchase Order',
        copy=False,
        store=True
    )

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Clear PO and GR fields when vendor changes"""
        res = super(AccountMove, self)._onchange_partner_id()
        if self.move_type in ['in_invoice', 'in_refund']:
            self.po_number = False
            self.goods_receipt_number = False
            self.awb_number = False
            self.warehouse_id = False
            self.buyer_id = False
        return res

    @api.onchange('purchase_vendor_bill_id', 'purchase_id')
    def _onchange_purchase_auto_complete(self):
        """Auto-fill PO Number, GR, AWB, Warehouse and Buyer when purchase order is selected via Auto-Complete"""
        res = super(AccountMove, self)._onchange_purchase_auto_complete()

        if self.purchase_vendor_bill_id and self.purchase_vendor_bill_id.purchase_order_id:
            po = self.purchase_vendor_bill_id.purchase_order_id

            # Auto-fill PO Number
            self.po_number = po

            # Auto-fill AWB from Purchase Order
            if hasattr(po, 'awb_number') and po.awb_number:
                self.awb_number = po.awb_number

            # Auto-fill Warehouse from PO picking_type_id
            if po.picking_type_id and po.picking_type_id.warehouse_id:
                self.warehouse_id = po.picking_type_id.warehouse_id

            # Auto-fill Buyer from PO user_id
            if po.user_id:
                self.buyer_id = po.user_id

            # Find related Goods Receipt (incoming picking)
            pickings = self.env['stock.picking'].search([
                ('purchase_id', '=', po.id),
                ('picking_type_id.code', '=', 'incoming'),
                ('state', '=', 'done')
            ], limit=1)

            if pickings:
                self.goods_receipt_number = pickings

        elif self.purchase_id:
            # Direct purchase_id field (alternative auto-complete method)
            po = self.purchase_id
            self.po_number = po

            # Auto-fill AWB from Purchase Order
            if hasattr(po, 'awb_number') and po.awb_number:
                self.awb_number = po.awb_number

            # Auto-fill Warehouse from PO picking_type_id
            if po.picking_type_id and po.picking_type_id.warehouse_id:
                self.warehouse_id = po.picking_type_id.warehouse_id

            # Auto-fill Buyer from PO user_id
            if po.user_id:
                self.buyer_id = po.user_id

            pickings = self.env['stock.picking'].search([
                ('purchase_id', '=', po.id),
                ('picking_type_id.code', '=', 'incoming'),
                ('state', '=', 'done')
            ], limit=1)

            if pickings:
                self.goods_receipt_number = pickings

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

            # Auto-fill Warehouse from PO picking_type_id
            if po.picking_type_id and po.picking_type_id.warehouse_id:
                self.warehouse_id = po.picking_type_id.warehouse_id

            # Auto-fill Buyer from PO user_id
            if po.user_id:
                self.buyer_id = po.user_id

            # Find related Goods Receipt
            pickings = self.env['stock.picking'].search([
                ('purchase_id', '=', po.id),
                ('picking_type_id.code', '=', 'incoming'),
                ('state', '=', 'done')
            ], limit=1)

            if pickings:
                self.goods_receipt_number = pickings

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
        """Update PO, AWB, Warehouse and Buyer when GR is selected"""
        if self.goods_receipt_number:
            gr = self.goods_receipt_number

            # If PO is not set, try to set it from GR
            if not self.po_number and gr.purchase_id:
                self.po_number = gr.purchase_id

                # Also get AWB from the related PO
                if hasattr(gr.purchase_id, 'awb_number') and gr.purchase_id.awb_number and not self.awb_number:
                    self.awb_number = gr.purchase_id.awb_number

                # Get Warehouse from the related PO
                if gr.purchase_id.picking_type_id and gr.purchase_id.picking_type_id.warehouse_id:
                    self.warehouse_id = gr.purchase_id.picking_type_id.warehouse_id

                # Get Buyer from the related PO
                if gr.purchase_id.user_id:
                    self.buyer_id = gr.purchase_id.user_id








# # -*- coding: utf-8 -*-
# from odoo import models, fields, api
#
#
# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#     # PO Number field (if not exists)
#     po_number = fields.Many2one(
#         'purchase.order',
#         string='PO Number',
#         domain="[('partner_id', '=', partner_id), ('state', 'in', ['purchase', 'done'])]",
#         help='Select Purchase Order'
#     )
#
#     # Goods Receipt field
#     goods_receipt_number = fields.Many2one(
#         'stock.picking',
#         string='Goods Receipt (GR)',
#         domain="[('partner_id', '=', partner_id), ('picking_type_id.code', '=', 'incoming'), ('state', '=', 'done')]",
#         help='Select Goods Receipt'
#     )
#
#     # AWB Number field (if not exists)
#     awb_number = fields.Char(
#         string='Shipping Ref#',
#         help='Air Waybill Number'
#     )
#
#     # Warehouse field (computed)
#     warehouse_id = fields.Many2one(
#         'stock.warehouse',
#         string='Warehouse',
#         compute='_compute_warehouse_id',
#         store=True,
#         readonly=True
#     )
#
#     @api.depends('po_number', 'goods_receipt_number')
#     def _compute_warehouse_id(self):
#         """Compute warehouse from PO or Goods Receipt"""
#         for move in self:
#             warehouse = False
#
#             # Try to get warehouse from Goods Receipt first
#             if move.goods_receipt_number and move.goods_receipt_number.picking_type_id:
#                 warehouse = move.goods_receipt_number.picking_type_id.warehouse_id
#
#             # If not found, try from PO
#             elif move.po_number and move.po_number.picking_type_id:
#                 warehouse = move.po_number.picking_type_id.warehouse_id
#
#             move.warehouse_id = warehouse
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