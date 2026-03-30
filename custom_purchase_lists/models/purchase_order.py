# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PurchaseOrder(models.Model):
    """
    Extends the purchase.order model with additional fields
    """
    _inherit = 'purchase.order'

    # AWB/Shipping Reference Number
    awb_number = fields.Char(
        string='AWB Number',
        help='Air Waybill or Shipping Reference Number',
        tracking=True,
        copy=False,
    )

    # Tax Amount (computed field)
    amount_tax = fields.Monetary(
        string='Tax Amount',
        store=True,
        readonly=True,
        compute='_compute_amount_tax',
        tracking=True,
        help='Total tax amount (Total Amount - Untaxed Amount)'
    )

    # Receipt Status
    receipt_status = fields.Selection([
        ('pending', 'Nothing to Receive'),
        ('partial', 'Partially Received'),
        ('full', 'Fully Received')
    ],
        string='Receipt Status',
        compute='_compute_receipt_status',
        store=True,
        help='Current receipt status based on received quantities'
    )

    # Date display fields (dd/mm/yy format for list views)
    date_order_display = fields.Char(
        string='Quotation Date',
        compute='_compute_date_displays',
        store=False,
    )

    date_approve_display = fields.Char(
        string='Order Date',
        compute='_compute_date_displays',
        store=False,
    )

    date_planned_display = fields.Char(
        string='Expected Arrival',
        compute='_compute_date_displays',
        store=False,
    )

    # Company currency for column visibility
    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Company Currency',
        store=False,
        readonly=True,
    )

    # -------------------------------------------------------
    # SAR converted amount fields for list views
    # Uses manual_currency_rate from purchase_order_awb module
    # Falls back to system rate if manual rate not set
    # -------------------------------------------------------
    amount_untaxed_sar = fields.Monetary(
        string='Untaxed Amount (SAR)',
        compute='_compute_sar_amounts',
        currency_field='company_currency_id',
        store=True,
    )

    amount_tax_sar = fields.Monetary(
        string='Tax Amount (SAR)',
        compute='_compute_sar_amounts',
        currency_field='company_currency_id',
        store=True,
    )

    amount_total_sar = fields.Monetary(
        string='Total Amount (SAR)',
        compute='_compute_sar_amounts',
        currency_field='company_currency_id',
        store=True,
    )

    @api.depends(
        'amount_untaxed', 'amount_tax', 'amount_total',
        'currency_id', 'company_id', 'date_order',
        'manual_currency_rate',
    )
    def _compute_sar_amounts(self):
        """
        Convert amount fields to company currency (SAR)
        using manual_currency_rate when set, else system rate.
        """
        for order in self:
            company = order.company_id
            order_currency = order.currency_id
            company_currency = company.currency_id

            # Same currency — no conversion needed
            if not order_currency or order_currency == company_currency:
                order.amount_untaxed_sar = order.amount_untaxed
                order.amount_tax_sar = order.amount_tax
                order.amount_total_sar = order.amount_total
                continue

            # Get rate: prefer manual, fallback to system
            rate = 0.0
            if hasattr(order, 'manual_currency_rate') and order.manual_currency_rate:
                rate = order.manual_currency_rate

            if not rate:
                rate_date = order.date_order.date() if order.date_order else fields.Date.today()
                try:
                    rate_record = self.env['res.currency.rate'].search([
                        ('currency_id', '=', order_currency.id),
                        ('company_id', '=', company.id),
                        ('name', '<=', str(rate_date)),
                    ], order='name desc', limit=1)
                    if rate_record and rate_record.inverse_company_rate:
                        rate = rate_record.inverse_company_rate
                    else:
                        rates = order_currency._get_rates(company, rate_date)
                        unit_per_sar = rates.get(order_currency.id, 1.0)
                        rate = (1.0 / unit_per_sar) if unit_per_sar else 1.0
                except Exception:
                    rate = 1.0

            order.amount_untaxed_sar = order.amount_untaxed * rate
            order.amount_tax_sar = order.amount_tax * rate
            order.amount_total_sar = order.amount_total * rate

    @api.depends('date_order', 'date_approve', 'date_planned')
    def _compute_date_displays(self):
        for order in self:
            order.date_order_display = (
                order.date_order.strftime('%d/%m/%y') if order.date_order else ''
            )
            order.date_approve_display = (
                order.date_approve.strftime('%d/%m/%y') if order.date_approve else ''
            )
            order.date_planned_display = (
                order.date_planned.strftime('%d/%m/%y') if order.date_planned else ''
            )

    @api.depends('amount_total', 'amount_untaxed')
    def _compute_amount_tax(self):
        for order in self:
            order.amount_tax = order.amount_total - order.amount_untaxed

    @api.depends('order_line.qty_received', 'order_line.product_qty')
    def _compute_receipt_status(self):
        for order in self:
            if not order.order_line:
                order.receipt_status = 'pending'
                continue
            total_qty = sum(order.order_line.mapped('product_qty'))
            received_qty = sum(order.order_line.mapped('qty_received'))
            if received_qty == 0:
                order.receipt_status = 'pending'
            elif received_qty >= total_qty:
                order.receipt_status = 'full'
            else:
                order.receipt_status = 'partial'








# # -*- coding: utf-8 -*-
# from odoo import models, fields, api
#
#
# class PurchaseOrder(models.Model):
#     """
#     Extends the purchase.order model with additional fields
#     """
#     _inherit = 'purchase.order'
#
#     # AWB/Shipping Reference Number
#     awb_number = fields.Char(
#         string='AWB Number',
#         help='Air Waybill or Shipping Reference Number',
#         tracking=True,
#         copy=False,
#     )
#
#     # Tax Amount (computed field)
#     amount_tax = fields.Monetary(
#         string='Tax Amount',
#         store=True,
#         readonly=True,
#         compute='_compute_amount_tax',
#         tracking=True,
#         help='Total tax amount (Total Amount - Untaxed Amount)'
#     )
#
#     # Receipt Status
#     receipt_status = fields.Selection([
#         ('pending', 'Nothing to Receive'),
#         ('partial', 'Partially Received'),
#         ('full', 'Fully Received')
#     ],
#         string='Receipt Status',
#         compute='_compute_receipt_status',
#         store=True,
#         help='Current receipt status based on received quantities'
#     )
#
#     # Date display fields (dd/mm/yy format for list views)
#     date_order_display = fields.Char(
#         string='Quotation Date',
#         compute='_compute_date_displays',
#         store=False,
#     )
#
#     date_approve_display = fields.Char(
#         string='Order Date',
#         compute='_compute_date_displays',
#         store=False,
#     )
#
#     date_planned_display = fields.Char(
#         string='Expected Arrival',
#         compute='_compute_date_displays',
#         store=False,
#     )
#
#     @api.depends('date_order', 'date_approve', 'date_planned')
#     def _compute_date_displays(self):
#         for order in self:
#             order.date_order_display = (
#                 order.date_order.strftime('%d/%m/%y') if order.date_order else ''
#             )
#             order.date_approve_display = (
#                 order.date_approve.strftime('%d/%m/%y') if order.date_approve else ''
#             )
#             order.date_planned_display = (
#                 order.date_planned.strftime('%d/%m/%y') if order.date_planned else ''
#             )
#
#     @api.depends('amount_total', 'amount_untaxed')
#     def _compute_amount_tax(self):
#         """
#         Compute tax amount as the difference between total and untaxed amounts
#         """
#         for order in self:
#             order.amount_tax = order.amount_total - order.amount_untaxed
#
#     @api.depends('order_line.qty_received', 'order_line.product_qty')
#     def _compute_receipt_status(self):
#         """
#         Compute receipt status based on received quantities
#         """
#         for order in self:
#             if not order.order_line:
#                 order.receipt_status = 'pending'
#                 continue
#
#             total_qty = sum(order.order_line.mapped('product_qty'))
#             received_qty = sum(order.order_line.mapped('qty_received'))
#
#             if received_qty == 0:
#                 order.receipt_status = 'pending'
#             elif received_qty >= total_qty:
#                 order.receipt_status = 'full'
#             else:
#                 order.receipt_status = 'partial'
#
#
