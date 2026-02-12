# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PurchaseOrder(models.Model):
    """
    Extends the purchase.order model with additional fields for tracking and display
    """
    _inherit = 'purchase.order'

    # ========================================
    # FIELDS
    # ========================================
    
    awb_number = fields.Char(
        string='AWB Number',
        help='Air Waybill or Shipping Reference Number',
        tracking=True,
        copy=False,
    )

    amount_tax = fields.Monetary(
        string='Tax Amount',
        store=True,
        readonly=True,
        compute='_compute_amount_tax',
        tracking=True,
        help='Total tax amount (Total Amount - Untaxed Amount)'
    )

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

    # ========================================
    # COMPUTE METHODS
    # ========================================

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
        Compute receipt status based on received quantities vs ordered quantities
        - pending: Nothing received yet (qty_received = 0)
        - partial: Some items received but not all
        - full: All items received (qty_received >= product_qty)
        """
        for order in self:
            # If no order lines, status is pending
            if not order.order_line:
                order.receipt_status = 'pending'
                continue

            # Calculate total ordered and received quantities
            total_qty = sum(order.order_line.mapped('product_qty'))
            received_qty = sum(order.order_line.mapped('qty_received'))

            # Determine status based on quantities
            if received_qty == 0:
                order.receipt_status = 'pending'
            elif received_qty >= total_qty:
                order.receipt_status = 'full'
            else:
                order.receipt_status = 'partial'
