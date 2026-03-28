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
    # FIX 1: Editable currency rate "1 USD = [3.750000] SAR"
    # Auto-filled from system rate, manually editable per bill
    # -------------------------------------------------------
    manual_currency_rate = fields.Float(
        string='Currency Rate',
        digits=(12, 6),
        store=True,
        copy=False,
        compute='_compute_manual_currency_rate',
        inverse='_inverse_manual_currency_rate',
        readonly=False,
        help='Exchange rate: how many SAR = 1 invoice currency. '
             'Auto-filled from system rate but can be changed manually.',
    )

    # Internal stored field to preserve manual overrides
    manual_currency_rate_stored = fields.Float(
        string='Currency Rate (Stored)',
        digits=(12, 6),
        store=True,
        copy=False,
    )

    currency_rate_prefix = fields.Char(
        compute='_compute_currency_rate_affixes',
        store=False,
    )
    currency_rate_suffix = fields.Char(
        compute='_compute_currency_rate_affixes',
        store=False,
    )

    @api.depends('currency_id', 'company_id')
    def _compute_currency_rate_affixes(self):
        for move in self:
            company_currency = move.company_id.currency_id
            invoice_currency = move.currency_id
            if invoice_currency and company_currency and invoice_currency != company_currency:
                move.currency_rate_prefix = "1 %s =" % invoice_currency.name
                move.currency_rate_suffix = company_currency.name
            else:
                move.currency_rate_prefix = ""
                move.currency_rate_suffix = ""

    def _get_system_rate(self, invoice_currency, company_id, rate_date):
        """Get SAR per 1 unit of invoice_currency from system rates."""
        rate_record = self.env['res.currency.rate'].search([
            ('currency_id', '=', invoice_currency.id),
            ('company_id', '=', company_id),
            ('name', '<=', str(rate_date)),
        ], order='name desc', limit=1)
        if rate_record and rate_record.inverse_company_rate:
            return rate_record.inverse_company_rate
        else:
            rate = invoice_currency._get_rates(
                self.env['res.company'].browse(company_id),
                rate_date
            )
            unit_per_sar = rate.get(invoice_currency.id, 1.0)
            return (1.0 / unit_per_sar) if unit_per_sar else 1.0

    @api.depends('currency_id', 'company_id', 'invoice_date', 'date',
                 'manual_currency_rate_stored')
    def _compute_manual_currency_rate(self):
        """
        Show stored rate if manually set (non-zero),
        otherwise auto-compute from system rates.
        """
        for move in self:
            company_currency = move.company_id.currency_id
            invoice_currency = move.currency_id
            if invoice_currency and company_currency and invoice_currency != company_currency:
                if move.manual_currency_rate_stored:
                    move.manual_currency_rate = move.manual_currency_rate_stored
                else:
                    rate_date = move.invoice_date or move.date or fields.Date.today()
                    move.manual_currency_rate = self._get_system_rate(
                        invoice_currency, move.company_id.id, rate_date
                    )
            else:
                move.manual_currency_rate = 1.0

    def _inverse_manual_currency_rate(self):
        """Save user's manual rate into the stored field
        AND write to invoice_currency_rate so accounting entries use it."""
        for move in self:
            move.manual_currency_rate_stored = move.manual_currency_rate
            # Write manual rate into Odoo's built-in rate field
            # invoice_currency_rate = unit_per_company = 1 / (SAR per USD)
            # e.g. manual=4.0 → invoice_currency_rate = 0.25
            if move.manual_currency_rate and move.currency_id != move.company_id.currency_id:
                move.invoice_currency_rate = 1.0 / move.manual_currency_rate

    @api.onchange('manual_currency_rate')
    def _onchange_manual_currency_rate(self):
        """Update invoice_currency_rate immediately when manual rate changes."""
        for move in self:
            if move.manual_currency_rate and move.currency_id != move.company_id.currency_id:
                move.invoice_currency_rate = 1.0 / move.manual_currency_rate

    @api.onchange('currency_id', 'invoice_date', 'date')
    def _onchange_currency_auto_fill_rate(self):
        """Reset stored rate when currency or date changes so system rate is used.
        But only reset if not coming from a PO selection (stored rate is 0)."""
        for move in self:
            company_currency = move.company_id.currency_id
            invoice_currency = move.currency_id
            if invoice_currency and company_currency and invoice_currency != company_currency:
                if not move.manual_currency_rate_stored:
                    move.manual_currency_rate_stored = 0.0
            else:
                move.manual_currency_rate_stored = 0.0

    def action_post(self):
        """Apply manual currency rate to journal entries before posting."""
        self._sync_manual_rate_to_invoice_rate()
        return super().action_post()

    def write(self, vals):
        """When manual rate changes on saved record, update invoice_currency_rate."""
        res = super().write(vals)
        if any(k in vals for k in [
            'manual_currency_rate', 'manual_currency_rate_stored',
            'currency_id', 'invoice_date',
        ]):
            self._sync_manual_rate_to_invoice_rate()
        return res

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

            # Auto-fill currency rate from PO's manual rate
            if hasattr(purchase_order, 'manual_currency_rate') and purchase_order.manual_currency_rate:
                self.manual_currency_rate_stored = purchase_order.manual_currency_rate
                self.manual_currency_rate = purchase_order.manual_currency_rate
                self.invoice_currency_rate = 1.0 / purchase_order.manual_currency_rate
                self.manual_currency_rate = purchase_order.manual_currency_rate

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

            # Auto-fill currency rate from PO's manual rate
            if hasattr(po, 'manual_currency_rate') and po.manual_currency_rate:
                self.manual_currency_rate_stored = po.manual_currency_rate
                self.manual_currency_rate = po.manual_currency_rate
                self.invoice_currency_rate = 1.0 / po.manual_currency_rate
                self.manual_currency_rate = po.manual_currency_rate

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

                # Auto-fill currency rate from PO's manual rate
                if hasattr(po, 'manual_currency_rate') and po.manual_currency_rate:
                    self.manual_currency_rate_stored = po.manual_currency_rate
                    self.manual_currency_rate = po.manual_currency_rate
                    self.invoice_currency_rate = 1.0 / po.manual_currency_rate
                    self.manual_currency_rate = po.manual_currency_rate

    def _sync_manual_rate_to_invoice_rate(self):
        """
        Push manual_currency_rate into Odoo's invoice_currency_rate.
        invoice_currency_rate = units of invoice currency per 1 company currency
        e.g. if 1 USD = 4 SAR → invoice_currency_rate = 1/4 = 0.25
        This makes journal entries use our manual rate for SAR amounts.
        """
        for move in self:
            company_currency = move.company_id.currency_id
            invoice_currency = move.currency_id
            if (invoice_currency and company_currency
                    and invoice_currency != company_currency
                    and move.manual_currency_rate
                    and move.manual_currency_rate > 0):
                # Write directly to invoice_currency_rate
                move.invoice_currency_rate = 1.0 / move.manual_currency_rate

    def write(self, vals):
        """Sync manual rate to invoice_currency_rate on every save."""
        result = super().write(vals)
        # Only sync when manual rate fields or currency fields changed
        if any(k in vals for k in [
            'manual_currency_rate', 'manual_currency_rate_stored',
            'currency_id', 'invoice_date',
        ]):
            self._sync_manual_rate_to_invoice_rate()
        return result

    def action_post(self):
        """Sync manual rate to invoice_currency_rate before posting."""
        self._sync_manual_rate_to_invoice_rate()
        return super().action_post()


class AccountMoveCompanyCurrency(models.Model):
    _inherit = 'account.move'

    # -------------------------------------------------------
    # FIX 2: Total amount in company currency shown below
    # the USD total — uses manual_currency_rate when set
    # e.g. Total: $500.00
    #              2,000.00 SR  (when rate = 4.0)
    # -------------------------------------------------------
    amount_total_in_company_currency = fields.Monetary(
        string='Total in Company Currency',
        compute='_compute_amount_total_in_company_currency',
        store=True,
        currency_field='company_currency_id',
        help='Invoice total converted to company currency (SAR) using manual rate'
    )

    @api.depends(
        'amount_total',
        'currency_id',
        'company_currency_id',
        'invoice_date',
        'date',
        'company_id',
        'manual_currency_rate',  # recompute when manual rate changes
        'manual_currency_rate_stored',  # recompute when stored rate changes
    )
    def _compute_amount_total_in_company_currency(self):
        """
        Convert amount_total from invoice currency (USD) to
        company currency (SAR) using manual_currency_rate.
        Formula: amount_total * manual_currency_rate = SAR total
        Falls back to system rate if manual rate is 0.
        """
        for move in self:
            company = move.company_id
            invoice_currency = move.currency_id
            company_currency = company.currency_id

            if not invoice_currency or not company_currency:
                move.amount_total_in_company_currency = move.amount_total
                continue

            if invoice_currency == company_currency:
                move.amount_total_in_company_currency = move.amount_total
            else:
                # Use manual rate if set, otherwise fall back to system rate
                rate = move.manual_currency_rate
                if rate:
                    move.amount_total_in_company_currency = move.amount_total * rate
                else:
                    # Fallback: use system currency conversion
                    rate_date = move.invoice_date or move.date or fields.Date.today()
                    converted = invoice_currency._convert(
                        move.amount_total,
                        company_currency,
                        company,
                        rate_date,
                    )
                    move.amount_total_in_company_currency = converted









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
