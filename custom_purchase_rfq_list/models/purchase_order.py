# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Add the missing awb_number field
    awb_number = fields.Char(
        string='AWB Number',
        help='Air Waybill or Shipping Reference Number'
    )

    amount_tax = fields.Monetary(
        string='Tax Amount',
        store=True,
        readonly=True,
        compute='_compute_amount_tax',
        tracking=True
    )

    receipt_status = fields.Selection([
        ('pending', 'Nothing to Receive'),
        ('partial', 'Partially Received'),
        ('full', 'Fully Received')
    ], string='Receipt Status', compute='_compute_receipt_status', store=True)

    @api.depends('amount_total', 'amount_untaxed')
    def _compute_amount_tax(self):
        """Compute tax amount as difference between total and untaxed"""
        for order in self:
            order.amount_tax = order.amount_total - order.amount_untaxed

    @api.depends('order_line.qty_received', 'order_line.product_qty')
    def _compute_receipt_status(self):
        """Compute receipt status based on received quantities"""
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
#     _inherit = 'purchase.order'
#
#     amount_tax = fields.Monetary(
#         string='Tax Amount',
#         store=True,
#         readonly=True,
#         compute='_compute_amount_tax',
#         tracking=True
#     )
#
#     receipt_status = fields.Selection([
#         ('pending', 'Nothing to Receive'),
#         ('partial', 'Partially Received'),
#         ('full', 'Fully Received')
#     ], string='Receipt Status', compute='_compute_receipt_status', store=True)
#
#     @api.depends('amount_total', 'amount_untaxed')
#     def _compute_amount_tax(self):
#         """Compute tax amount as difference between total and untaxed"""
#         for order in self:
#             order.amount_tax = order.amount_total - order.amount_untaxed
#
#     @api.depends('order_line.qty_received', 'order_line.product_qty')
#     def _compute_receipt_status(self):
#         """Compute receipt status based on received quantities"""
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