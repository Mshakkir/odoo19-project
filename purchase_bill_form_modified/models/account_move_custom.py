from odoo import models, fields, api
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    # PO Number field
    po_number = fields.Many2one(
        'purchase.order',
        string='PO Number',
        domain="[('partner_id', '=', partner_id), ('state', 'in', ['purchase', 'done'])]",
        help='Select Purchase Order'
    )

    # Goods Receipt field
    goods_receipt_number = fields.Many2one(
        'stock.picking',
        string='Goods Receipt (GR)',
        domain="[('partner_id', '=', partner_id), ('picking_type_id.code', '=', 'incoming'), ('state', '=', 'done')]",
        help='Select Goods Receipt'
    )

    # AWB Number field
    awb_number = fields.Char(
        string='Shipping Ref#',
        help='Air Waybill Number'
    )

    # Deliver To field from Purchase Order (picking_type_id)
    deliver_to = fields.Many2one(
        'stock.picking.type',
        string='Deliver To',
        help='Delivery destination from Purchase Order'
    )

    # Buyer field from Purchase Order (user_id)
    buyer_id = fields.Many2one(
        'res.users',
        string='Buyer',
        help='Buyer from Purchase Order'
    )

    # Warehouse field (computed)
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        compute='_compute_warehouse_id',
        store=True,
        readonly=True
    )

    @api.depends('po_number', 'goods_receipt_number', 'deliver_to')
    def _compute_warehouse_id(self):
        """Compute warehouse from PO or Goods Receipt or Deliver To"""
        for move in self:
            warehouse = False

            # Try to get warehouse from Deliver To first
            if move.deliver_to and move.deliver_to.warehouse_id:
                warehouse = move.deliver_to.warehouse_id
            # Try to get warehouse from Goods Receipt
            elif move.goods_receipt_number and move.goods_receipt_number.picking_type_id:
                warehouse = move.goods_receipt_number.picking_type_id.warehouse_id
            # If not found, try from PO
            elif move.po_number and move.po_number.picking_type_id:
                warehouse = move.po_number.picking_type_id.warehouse_id

            move.warehouse_id = warehouse

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Clear PO and GR fields when vendor changes"""
        res = super(AccountMove, self)._onchange_partner_id()
        if self.move_type in ['in_invoice', 'in_refund']:
            self.po_number = False
            self.goods_receipt_number = False
            self.awb_number = False
            self.deliver_to = False
            self.buyer_id = False
        return res

    @api.onchange('purchase_vendor_bill_id', 'purchase_id')
    def _onchange_purchase_auto_complete(self):
        """Auto-fill PO Number, GR, AWB, Deliver To, and Buyer when purchase order is selected via Auto-Complete"""
        res = super(AccountMove, self)._onchange_purchase_auto_complete()

        purchase_order = False

        if self.purchase_vendor_bill_id and self.purchase_vendor_bill_id.purchase_order_id:
            purchase_order = self.purchase_vendor_bill_id.purchase_order_id
        elif self.purchase_id:
            purchase_order = self.purchase_id

        if purchase_order:
            # Auto-fill PO Number
            self.po_number = purchase_order

            # Auto-fill Buyer (user_id from PO)
            if purchase_order.user_id:
                self.buyer_id = purchase_order.user_id

            # Auto-fill Deliver To (picking_type_id from PO)
            if purchase_order.picking_type_id:
                self.deliver_to = purchase_order.picking_type_id

            # Auto-fill AWB from Purchase Order (if exists)
            if hasattr(purchase_order, 'awb_number') and purchase_order.awb_number:
                self.awb_number = purchase_order.awb_number

            # Find related Goods Receipt (incoming picking)
            pickings = self.env['stock.picking'].search([
                ('purchase_id', '=', purchase_order.id),
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

            # Auto-fill Buyer (user_id from PO)
            if po.user_id:
                self.buyer_id = po.user_id

            # Auto-fill Deliver To (picking_type_id from PO)
            if po.picking_type_id:
                self.deliver_to = po.picking_type_id

            # Auto-fill AWB from Purchase Order
            if hasattr(po, 'awb_number') and po.awb_number:
                self.awb_number = po.awb_number

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
                                'tax_ids': [(6, 0, line.tax_ids.ids)],
                                'purchase_line_id': line.id,
                            }))
                if lines_data:
                    self.invoice_line_ids = lines_data

    @api.onchange('goods_receipt_number')
    def _onchange_goods_receipt(self):
        """Update PO, AWB, Deliver To, and Buyer when GR is selected"""
        if self.goods_receipt_number:
            gr = self.goods_receipt_number

            # If PO is not set, try to set it from GR
            if not self.po_number and gr.purchase_id:
                po = gr.purchase_id
                self.po_number = po

                # Get Buyer from the related PO
                if po.user_id:
                    self.buyer_id = po.user_id

                # Get Deliver To from the related PO
                if po.picking_type_id:
                    self.deliver_to = po.picking_type_id

                # Also get AWB from the related PO
                if hasattr(po, 'awb_number') and po.awb_number:
                    self.awb_number = po.awb_number

    def _link_purchase_orders_from_lines(self):
        """
        Link all purchase orders from invoice lines to ensure proper billing status tracking.
        This method ensures that all POs referenced in the invoice lines are properly linked.
        """
        for move in self:
            if move.move_type in ['in_invoice', 'in_refund']:
                # Collect all unique purchase orders from invoice lines
                purchase_orders = move.invoice_line_ids.mapped('purchase_line_id.order_id')

                if purchase_orders:
                    # Set the primary PO in purchase_id field (Odoo standard field)
                    if move.po_number and move.po_number in purchase_orders:
                        # Use the PO from po_number field as primary
                        move.purchase_id = move.po_number
                    elif not move.purchase_id and purchase_orders:
                        # If no purchase_id is set, use the first one from lines
                        move.purchase_id = purchase_orders[0]

    def action_post(self):
        """
        Override action_post to ensure purchase orders are properly linked before posting.
        This ensures the billing status is updated correctly for ALL purchase orders.
        """
        # First, link purchase orders from invoice lines
        self._link_purchase_orders_from_lines()

        # Call the parent method to post the invoice
        res = super(AccountMove, self).action_post()

        # After posting, manually update invoice_status for all related POs
        # This is necessary because Odoo's purchase_id field only tracks ONE PO
        for move in self:
            if move.move_type in ['in_invoice', 'in_refund'] and move.state == 'posted':
                # Get all unique purchase orders from invoice lines
                purchase_orders = move.invoice_line_ids.mapped('purchase_line_id.order_id')

                if purchase_orders:
                    # Force recompute of invoice status for all related POs
                    purchase_orders._compute_invoice_status()

        return res

    def button_draft(self):
        """
        Override button_draft to update PO status when resetting to draft.
        """
        # Get all related purchase orders before resetting to draft
        purchase_orders = self.invoice_line_ids.mapped('purchase_line_id.order_id')

        res = super(AccountMove, self).button_draft()

        # Re-link purchase orders when going back to draft
        self._link_purchase_orders_from_lines()

        # Recompute invoice status for all related POs
        if purchase_orders:
            purchase_orders._compute_invoice_status()

        return res

    def button_cancel(self):
        """
        Override button_cancel to update PO status when canceling.
        """
        # Get all related purchase orders before canceling
        purchase_orders = self.invoice_line_ids.mapped('purchase_line_id.order_id')

        res = super(AccountMove, self).button_cancel()

        # Recompute invoice status for all related POs
        if purchase_orders:
            purchase_orders._compute_invoice_status()

        return res

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to ensure purchase order linkage on creation.
        """
        moves = super(AccountMove, self).create(vals_list)
        # Link purchase orders after creation
        moves._link_purchase_orders_from_lines()
        return moves

    def write(self, vals):
        """
        Override write to maintain purchase order linkage and status updates.
        """
        # Get related POs before write
        old_purchase_orders = self.invoice_line_ids.mapped('purchase_line_id.order_id')

        res = super(AccountMove, self).write(vals)

        # If invoice lines are updated, re-link purchase orders
        if 'invoice_line_ids' in vals or 'state' in vals:
            self._link_purchase_orders_from_lines()

            # Get new related POs after write
            new_purchase_orders = self.invoice_line_ids.mapped('purchase_line_id.order_id')

            # Combine old and new POs to ensure all are updated
            all_purchase_orders = old_purchase_orders | new_purchase_orders

            if all_purchase_orders:
                all_purchase_orders._compute_invoice_status()

        return res

    def unlink(self):
        """
        Override unlink to update PO status when deleting invoices.
        """
        # Get all related purchase orders before deletion
        purchase_orders = self.invoice_line_ids.mapped('purchase_line_id.order_id')

        res = super(AccountMove, self).unlink()

        # Recompute invoice status for all related POs after deletion
        if purchase_orders:
            purchase_orders._compute_invoice_status()

        return res








# from odoo import models, fields, api
# from odoo.exceptions import UserError
#
#
# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#     # PO Number field
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
#     # AWB Number field
#     awb_number = fields.Char(
#         string='Shipping Ref#',
#         help='Air Waybill Number'
#     )
#
#     # Deliver To field from Purchase Order (picking_type_id)
#     deliver_to = fields.Many2one(
#         'stock.picking.type',
#         string='Deliver To',
#         help='Delivery destination from Purchase Order'
#     )
#
#     # Buyer field from Purchase Order (user_id)
#     buyer_id = fields.Many2one(
#         'res.users',
#         string='Buyer',
#         help='Buyer from Purchase Order'
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
#     @api.depends('po_number', 'goods_receipt_number', 'deliver_to')
#     def _compute_warehouse_id(self):
#         """Compute warehouse from PO or Goods Receipt or Deliver To"""
#         for move in self:
#             warehouse = False
#
#             # Try to get warehouse from Deliver To first
#             if move.deliver_to and move.deliver_to.warehouse_id:
#                 warehouse = move.deliver_to.warehouse_id
#             # Try to get warehouse from Goods Receipt
#             elif move.goods_receipt_number and move.goods_receipt_number.picking_type_id:
#                 warehouse = move.goods_receipt_number.picking_type_id.warehouse_id
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
#             self.deliver_to = False
#             self.buyer_id = False
#         return res
#
#     @api.onchange('purchase_vendor_bill_id', 'purchase_id')
#     def _onchange_purchase_auto_complete(self):
#         """Auto-fill PO Number, GR, AWB, Deliver To, and Buyer when purchase order is selected via Auto-Complete"""
#         res = super(AccountMove, self)._onchange_purchase_auto_complete()
#
#         purchase_order = False
#
#         if self.purchase_vendor_bill_id and self.purchase_vendor_bill_id.purchase_order_id:
#             purchase_order = self.purchase_vendor_bill_id.purchase_order_id
#         elif self.purchase_id:
#             purchase_order = self.purchase_id
#
#         if purchase_order:
#             # Auto-fill PO Number
#             self.po_number = purchase_order
#
#             # Auto-fill Buyer (user_id from PO)
#             if purchase_order.user_id:
#                 self.buyer_id = purchase_order.user_id
#
#             # Auto-fill Deliver To (picking_type_id from PO)
#             if purchase_order.picking_type_id:
#                 self.deliver_to = purchase_order.picking_type_id
#
#             # Auto-fill AWB from Purchase Order (if exists)
#             if hasattr(purchase_order, 'awb_number') and purchase_order.awb_number:
#                 self.awb_number = purchase_order.awb_number
#
#             # Find related Goods Receipt (incoming picking)
#             pickings = self.env['stock.picking'].search([
#                 ('purchase_id', '=', purchase_order.id),
#                 ('picking_type_id.code', '=', 'incoming'),
#                 ('state', '=', 'done')
#             ], limit=1)
#
#             if pickings:
#                 self.goods_receipt_number = pickings
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
#             # Auto-fill Buyer (user_id from PO)
#             if po.user_id:
#                 self.buyer_id = po.user_id
#
#             # Auto-fill Deliver To (picking_type_id from PO)
#             if po.picking_type_id:
#                 self.deliver_to = po.picking_type_id
#
#             # Auto-fill AWB from Purchase Order
#             if hasattr(po, 'awb_number') and po.awb_number:
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
#                 self.goods_receipt_number = pickings
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
#                                 'tax_ids': [(6, 0, line.tax_ids.ids)],  # FIXED: Changed from taxes_id to tax_ids
#                                 'purchase_line_id': line.id,
#                             }))
#                 if lines_data:
#                     self.invoice_line_ids = lines_data
#
#     @api.onchange('goods_receipt_number')
#     def _onchange_goods_receipt(self):
#         """Update PO, AWB, Deliver To, and Buyer when GR is selected"""
#         if self.goods_receipt_number:
#             gr = self.goods_receipt_number
#
#             # If PO is not set, try to set it from GR
#             if not self.po_number and gr.purchase_id:
#                 po = gr.purchase_id
#                 self.po_number = po
#
#                 # Get Buyer from the related PO
#                 if po.user_id:
#                     self.buyer_id = po.user_id
#
#                 # Get Deliver To from the related PO
#                 if po.picking_type_id:
#                     self.deliver_to = po.picking_type_id
#
#                 # Also get AWB from the related PO
#                 if hasattr(po, 'awb_number') and po.awb_number:
#                     self.awb_number = po.awb_number