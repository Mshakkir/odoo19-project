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

    # Delivery Address field (own company delivery addresses)
    delivery_address_id = fields.Many2one(
        'res.partner',
        string='Delivery Address',
        help='Delivery address for this vendor bill',
        copy=True,
    )

    # Warehouse field (computed)
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        compute='_compute_warehouse_id',
        store=True,
        readonly=True
    )

    # -------------------------------------------------------
    # FIX 1: Currency rate display as "1 USD = X SAR"
    # Computed field: how many company currency units per 1 invoice currency unit
    # -------------------------------------------------------
    currency_rate_display = fields.Float(
        string='Currency Rate',
        compute='_compute_currency_rate_display',
        store=False,
        digits=(12, 6),
        help='Exchange rate: 1 [invoice currency] = X [company currency]'
    )

    currency_rate_label = fields.Char(
        string='Currency Rate Label',
        compute='_compute_currency_rate_display',
        store=False,
        help='Display label for exchange rate'
    )

    @api.depends('currency_id', 'company_id', 'invoice_date', 'date')
    def _compute_currency_rate_display(self):
        """
        Compute rate as: 1 [invoice_currency] = X [company_currency]
        Example: 1 USD = 3.75 SAR
        """
        for move in self:
            company_currency = move.company_id.currency_id
            invoice_currency = move.currency_id
            if invoice_currency and company_currency and invoice_currency != company_currency:
                # Get the rate date
                rate_date = move.invoice_date or move.date or fields.Date.today()
                # currency_id.rate gives: 1 company_currency = X invoice_currency (unit per SAR)
                # We want: 1 invoice_currency = X company_currency (SAR per unit)
                # So we compute: 1 / (unit_per_SAR) = SAR_per_unit
                rate = invoice_currency._get_rates(move.company_id, rate_date)
                unit_per_company = rate.get(invoice_currency.id, 1.0)
                if unit_per_company:
                    sar_per_unit = 1.0 / unit_per_company
                else:
                    sar_per_unit = 1.0
                move.currency_rate_display = sar_per_unit
                move.currency_rate_label = "1 %s = %.6f %s" % (
                    invoice_currency.name,
                    sar_per_unit,
                    company_currency.name
                )
            else:
                move.currency_rate_display = 1.0
                move.currency_rate_label = ""

    @api.depends('po_number', 'goods_receipt_number', 'deliver_to')
    def _compute_warehouse_id(self):
        """Compute warehouse from PO or Goods Receipt or Deliver To"""
        for move in self:
            warehouse = False
            if move.deliver_to and move.deliver_to.warehouse_id:
                warehouse = move.deliver_to.warehouse_id
            elif move.goods_receipt_number and move.goods_receipt_number.picking_type_id:
                warehouse = move.goods_receipt_number.picking_type_id.warehouse_id
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
        """Auto-fill PO Number, GR, AWB, Deliver To, Buyer and Delivery Address when PO is selected via Auto-Complete"""
        res = super(AccountMove, self)._onchange_purchase_auto_complete()

        purchase_order = False
        if self.purchase_vendor_bill_id and self.purchase_vendor_bill_id.purchase_order_id:
            purchase_order = self.purchase_vendor_bill_id.purchase_order_id
        elif self.purchase_id:
            purchase_order = self.purchase_id

        if purchase_order:
            self.po_number = purchase_order

            if purchase_order.user_id:
                self.buyer_id = purchase_order.user_id

            if purchase_order.picking_type_id:
                self.deliver_to = purchase_order.picking_type_id

            if hasattr(purchase_order, 'awb_number') and purchase_order.awb_number:
                self.awb_number = purchase_order.awb_number

            if hasattr(purchase_order, 'delivery_address_id') and purchase_order.delivery_address_id:
                self.delivery_address_id = purchase_order.delivery_address_id

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

            if not self.ref:
                self.ref = po.name

            if not self.invoice_date:
                self.invoice_date = fields.Date.today()

            if po.user_id:
                self.buyer_id = po.user_id

            if po.picking_type_id:
                self.deliver_to = po.picking_type_id

            if hasattr(po, 'awb_number') and po.awb_number:
                self.awb_number = po.awb_number

            if hasattr(po, 'delivery_address_id') and po.delivery_address_id:
                self.delivery_address_id = po.delivery_address_id

            pickings = self.env['stock.picking'].search([
                ('purchase_id', '=', po.id),
                ('picking_type_id.code', '=', 'incoming'),
                ('state', '=', 'done')
            ], limit=1)
            if pickings:
                self.goods_receipt_number = pickings

            if not self.invoice_line_ids:
                lines_data = []
                for line in po.order_line:
                    if line.product_id:
                        account = line.product_id.property_account_expense_id or \
                                  line.product_id.categ_id.property_account_expense_categ_id
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
        """Update PO, AWB, Deliver To, Buyer and Delivery Address when GR is selected"""
        if self.goods_receipt_number:
            gr = self.goods_receipt_number
            if not self.po_number and gr.purchase_id:
                po = gr.purchase_id
                self.po_number = po

                if po.user_id:
                    self.buyer_id = po.user_id

                if po.picking_type_id:
                    self.deliver_to = po.picking_type_id

                if hasattr(po, 'awb_number') and po.awb_number:
                    self.awb_number = po.awb_number

                if hasattr(po, 'delivery_address_id') and po.delivery_address_id:
                    self.delivery_address_id = po.delivery_address_id


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # -------------------------------------------------------
    # FIX 2: Total amount in company currency per invoice line
    # -------------------------------------------------------
    total_company_currency = fields.Monetary(
        string='Total (SAR)',
        compute='_compute_total_company_currency',
        store=True,
        currency_field='company_currency_id',
        help='Total amount converted to company currency (SAR)'
    )

    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Company Currency',
        store=False,
        readonly=True,
    )

    @api.depends(
        'price_subtotal',
        'currency_id',
        'company_currency_id',
        'move_id.invoice_date',
        'move_id.date',
        'move_id.company_id',
    )
    def _compute_total_company_currency(self):
        """
        Convert line total (price_subtotal) from invoice currency to company currency.
        price_subtotal is in invoice currency (e.g. USD).
        We convert it to company currency (e.g. SAR).
        """
        for line in self:
            company = line.company_id
            invoice_currency = line.currency_id
            company_currency = company.currency_id

            if not invoice_currency or not company_currency:
                line.total_company_currency = line.price_subtotal
                continue

            if invoice_currency == company_currency:
                line.total_company_currency = line.price_subtotal
            else:
                rate_date = line.move_id.invoice_date or line.move_id.date or fields.Date.today()
                converted = invoice_currency._convert(
                    line.price_subtotal,
                    company_currency,
                    company,
                    rate_date,
                )
                line.total_company_currency = converted














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
#     # Delivery Address field (own company delivery addresses)
#     delivery_address_id = fields.Many2one(
#         'res.partner',
#         string='Delivery Address',
#         help='Delivery address for this vendor bill',
#         copy=True,
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
#             if move.deliver_to and move.deliver_to.warehouse_id:
#                 warehouse = move.deliver_to.warehouse_id
#             elif move.goods_receipt_number and move.goods_receipt_number.picking_type_id:
#                 warehouse = move.goods_receipt_number.picking_type_id.warehouse_id
#             elif move.po_number and move.po_number.picking_type_id:
#                 warehouse = move.po_number.picking_type_id.warehouse_id
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
#         """Auto-fill PO Number, GR, AWB, Deliver To, Buyer and Delivery Address when PO is selected via Auto-Complete"""
#         res = super(AccountMove, self)._onchange_purchase_auto_complete()
#
#         purchase_order = False
#         if self.purchase_vendor_bill_id and self.purchase_vendor_bill_id.purchase_order_id:
#             purchase_order = self.purchase_vendor_bill_id.purchase_order_id
#         elif self.purchase_id:
#             purchase_order = self.purchase_id
#
#         if purchase_order:
#             self.po_number = purchase_order
#
#             if purchase_order.user_id:
#                 self.buyer_id = purchase_order.user_id
#
#             if purchase_order.picking_type_id:
#                 self.deliver_to = purchase_order.picking_type_id
#
#             if hasattr(purchase_order, 'awb_number') and purchase_order.awb_number:
#                 self.awb_number = purchase_order.awb_number
#
#             # Auto-fill Delivery Address from PO
#             if hasattr(purchase_order, 'delivery_address_id') and purchase_order.delivery_address_id:
#                 self.delivery_address_id = purchase_order.delivery_address_id
#
#             pickings = self.env['stock.picking'].search([
#                 ('purchase_id', '=', purchase_order.id),
#                 ('picking_type_id.code', '=', 'incoming'),
#                 ('state', '=', 'done')
#             ], limit=1)
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
#             if not self.ref:
#                 self.ref = po.name
#
#             if not self.invoice_date:
#                 self.invoice_date = fields.Date.today()
#
#             if po.user_id:
#                 self.buyer_id = po.user_id
#
#             if po.picking_type_id:
#                 self.deliver_to = po.picking_type_id
#
#             if hasattr(po, 'awb_number') and po.awb_number:
#                 self.awb_number = po.awb_number
#
#             # Auto-fill Delivery Address from PO
#             if hasattr(po, 'delivery_address_id') and po.delivery_address_id:
#                 self.delivery_address_id = po.delivery_address_id
#
#             pickings = self.env['stock.picking'].search([
#                 ('purchase_id', '=', po.id),
#                 ('picking_type_id.code', '=', 'incoming'),
#                 ('state', '=', 'done')
#             ], limit=1)
#             if pickings:
#                 self.goods_receipt_number = pickings
#
#             if not self.invoice_line_ids:
#                 lines_data = []
#                 for line in po.order_line:
#                     if line.product_id:
#                         account = line.product_id.property_account_expense_id or \
#                                   line.product_id.categ_id.property_account_expense_categ_id
#                         qty_to_invoice = line.product_qty - line.qty_invoiced
#                         if qty_to_invoice > 0:
#                             lines_data.append((0, 0, {
#                                 'product_id': line.product_id.id,
#                                 'quantity': qty_to_invoice,
#                                 'price_unit': line.price_unit,
#                                 'name': line.name,
#                                 'account_id': account.id if account else False,
#                                 'tax_ids': [(6, 0, line.tax_ids.ids)],
#                                 'purchase_line_id': line.id,
#                             }))
#                 if lines_data:
#                     self.invoice_line_ids = lines_data
#
#     @api.onchange('goods_receipt_number')
#     def _onchange_goods_receipt(self):
#         """Update PO, AWB, Deliver To, Buyer and Delivery Address when GR is selected"""
#         if self.goods_receipt_number:
#             gr = self.goods_receipt_number
#             if not self.po_number and gr.purchase_id:
#                 po = gr.purchase_id
#                 self.po_number = po
#
#                 if po.user_id:
#                     self.buyer_id = po.user_id
#
#                 if po.picking_type_id:
#                     self.deliver_to = po.picking_type_id
#
#                 if hasattr(po, 'awb_number') and po.awb_number:
#                     self.awb_number = po.awb_number
#
#                 # Auto-fill Delivery Address from PO
#                 if hasattr(po, 'delivery_address_id') and po.delivery_address_id:
#                     self.delivery_address_id = po.delivery_address_id
