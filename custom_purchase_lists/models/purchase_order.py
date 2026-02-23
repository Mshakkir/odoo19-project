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
        """
        Compute tax amount as the difference between total and untaxed amounts
        """
        for order in self:
            order.amount_tax = order.amount_total - order.amount_untaxed

    @api.depends('order_line.qty_received', 'order_line.product_qty')
    def _compute_receipt_status(self):
        """
        Compute receipt status based on received quantities
        """
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


