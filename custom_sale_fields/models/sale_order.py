from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    awb_number = fields.Char(
        string='Shipping Ref #',
        help='Air Waybill Number',
        copy=False
    )

    # ── Override currency_id to make it directly selectable ─────────────────
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        ondelete='restrict',
        store=True,
        readonly=False,
        compute='_compute_currency_id',
        inverse='_inverse_currency_id',
        help='Select the currency for this sale order.',
    )

    sale_currency_id = fields.Many2one(
        'res.currency',
        string='Manual Currency',
        store=True,
        copy=True,
    )

    @api.depends('pricelist_id', 'sale_currency_id', 'company_id')
    def _compute_currency_id(self):
        for order in self:
            if order.sale_currency_id:
                order.currency_id = order.sale_currency_id
            elif order.pricelist_id:
                order.currency_id = order.pricelist_id.currency_id
            else:
                order.currency_id = order.company_id.currency_id

    def _inverse_currency_id(self):
        for order in self:
            order.sale_currency_id = order.currency_id

    # ── Manual Currency Rate Fields ──────────────────────────────────────────
    manual_currency_rate = fields.Float(
        string='Currency Rate',
        digits=(12, 6),
        store=True,
        copy=False,
        help='Exchange rate: how many SAR = 1 order currency.',
    )

    currency_rate_prefix = fields.Char(
        compute='_compute_currency_rate_affixes',
        store=False,
    )
    currency_rate_suffix = fields.Char(
        compute='_compute_currency_rate_affixes',
        store=False,
    )

    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Company Currency',
        store=False,
        readonly=True,
    )

    amount_total_company_currency = fields.Monetary(
        string='Total in Company Currency',
        compute='_compute_amount_total_company_currency',
        store=True,
        currency_field='company_currency_id',
    )

    # ── Compute Prefix/Suffix Labels ─────────────────────────────────────────
    @api.depends('currency_id', 'company_id')
    def _compute_currency_rate_affixes(self):
        for order in self:
            company_currency = order.company_id.currency_id
            order_currency = order.currency_id
            if order_currency and company_currency and order_currency != company_currency:
                order.currency_rate_prefix = "1 %s =" % order_currency.name
                order.currency_rate_suffix = company_currency.name
            else:
                order.currency_rate_prefix = ""
                order.currency_rate_suffix = ""

    # ── Compute Total in Company Currency ────────────────────────────────────
    @api.depends('amount_total', 'manual_currency_rate', 'currency_id', 'company_id')
    def _compute_amount_total_company_currency(self):
        for order in self:
            company_currency = order.company_id.currency_id
            order_currency = order.currency_id
            if order_currency and company_currency and order_currency != company_currency:
                rate = order.manual_currency_rate
                if not rate:
                    rate_date = order.date_order.date() if order.date_order else fields.Date.today()
                    rate = order._get_system_rate(order_currency, order.company_id.id, rate_date)
                order.amount_total_company_currency = order.amount_total * rate
            else:
                order.amount_total_company_currency = order.amount_total

    # ── System Rate Helper ───────────────────────────────────────────────────
    def _get_system_rate(self, order_currency, company_id, rate_date):
        rate_record = self.env['res.currency.rate'].search([
            ('currency_id', '=', order_currency.id),
            ('company_id', '=', company_id),
            ('name', '<=', str(rate_date)),
        ], order='name desc', limit=1)
        if rate_record and rate_record.inverse_company_rate:
            return rate_record.inverse_company_rate
        rate = order_currency._get_rates(
            self.env['res.company'].browse(company_id), rate_date
        )
        unit_per_sar = rate.get(order_currency.id, 1.0)
        return (1.0 / unit_per_sar) if unit_per_sar else 1.0

    # ── Auto-fill Rate on Currency / Date Change ─────────────────────────────
    @api.onchange('currency_id', 'sale_currency_id', 'date_order')
    def _onchange_currency_auto_fill_rate(self):
        for order in self:
            company_currency = order.company_id.currency_id
            order_currency = order.currency_id
            if order_currency and company_currency and order_currency != company_currency:
                rate_date = order.date_order.date() if order.date_order else fields.Date.today()
                order.manual_currency_rate = self._get_system_rate(
                    order_currency, order.company_id.id, rate_date
                )
            else:
                order.manual_currency_rate = 1.0

    # ── Existing Methods ─────────────────────────────────────────────────────
    def _prepare_invoice(self):
        """Override to pass PO Number, AWB, delivery note, currency and manual rate to invoice"""
        invoice_vals = super()._prepare_invoice()

        if self.client_order_ref:
            invoice_vals['client_order_ref'] = self.client_order_ref

        if self.awb_number:
            invoice_vals['awb_number'] = self.awb_number

        # ── Pass currency and manual rate to invoice ──────────────────────
        if self.currency_id:
            invoice_vals['currency_id'] = self.currency_id.id

        if self.manual_currency_rate:
            invoice_vals['manual_currency_rate'] = self.manual_currency_rate

        completed_pickings = self.picking_ids.filtered(
            lambda p: p.state == 'done' and p.picking_type_code == 'outgoing'
        )

        if completed_pickings:
            delivery_note_numbers = []
            for picking in completed_pickings:
                if hasattr(picking, 'delivery_note_number') and picking.delivery_note_number:
                    delivery_note_numbers.append(picking.delivery_note_number)
                elif picking.name:
                    delivery_note_numbers.append(picking.name)

            if delivery_note_numbers:
                invoice_vals['delivery_note_number'] = ', '.join(delivery_note_numbers)

            if not self.awb_number:
                for picking in completed_pickings:
                    if hasattr(picking, 'awb_number') and picking.awb_number:
                        invoice_vals['awb_number'] = picking.awb_number
                        break

        return invoice_vals

    def action_confirm(self):
        """Copy AWB number to delivery orders when sale order is confirmed"""
        result = super().action_confirm()
        if self.awb_number:
            for picking in self.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing'):
                if not picking.awb_number:
                    picking.awb_number = self.awb_number
        return result







# from odoo import models, fields, api
#
#
# class SaleOrder(models.Model):
#     _inherit = 'sale.order'
#
#     awb_number = fields.Char(
#         string='Shipping Ref #',
#         help='Air Waybill Number',
#         copy=False
#     )
#
#     def _prepare_invoice(self):
#         """Override to pass PO Number, AWB, and delivery note to invoice"""
#         invoice_vals = super()._prepare_invoice()
#
#         # Transfer PO Number (client_order_ref) to invoice client_order_ref field
#         if self.client_order_ref:
#             invoice_vals['client_order_ref'] = self.client_order_ref
#
#         # Transfer AWB Number from Sale Order
#         if self.awb_number:
#             invoice_vals['awb_number'] = self.awb_number
#
#         # Auto-populate Delivery Note Number from completed delivery orders
#         completed_pickings = self.picking_ids.filtered(
#             lambda p: p.state == 'done' and p.picking_type_code == 'outgoing'
#         )
#
#         if completed_pickings:
#             # Use the delivery order NAME (reference) as the delivery note number
#             # If there's a custom delivery_note_number field, use that, otherwise use the name
#             delivery_note_numbers = []
#
#             for picking in completed_pickings:
#                 # Priority 1: Custom delivery note number (if manually entered)
#                 if hasattr(picking, 'delivery_note_number') and picking.delivery_note_number:
#                     delivery_note_numbers.append(picking.delivery_note_number)
#                 # Priority 2: Use the delivery order reference (MAIN/OUT/00029)
#                 elif picking.name:
#                     delivery_note_numbers.append(picking.name)
#
#             # Join multiple delivery notes with comma if there are multiple deliveries
#             if delivery_note_numbers:
#                 invoice_vals['delivery_note_number'] = ', '.join(delivery_note_numbers)
#
#             # Get AWB from delivery if not set on sale order
#             if not self.awb_number:
#                 for picking in completed_pickings:
#                     if hasattr(picking, 'awb_number') and picking.awb_number:
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