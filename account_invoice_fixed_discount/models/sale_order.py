from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    global_discount_amount = fields.Monetary(
        string="Global Discount",
        default=0.0,
        currency_field="currency_id",
        help="Fixed discount applied on the total untaxed amount."
    )

    amount_after_discount = fields.Monetary(
        string="Total After Discount",
        compute="_compute_amount_after_discount",
        currency_field="currency_id",
        store=True
    )

    @api.depends('amount_untaxed', 'global_discount_amount')
    def _compute_amount_after_discount(self):
        for order in self:
            order.amount_after_discount = order.amount_untaxed - order.global_discount_amount

    @api.depends(
        'order_line.price_total',
        'global_discount_amount'
    )
    def _amount_all(self):
        """Override Odoo total computation to subtract global discount"""
        for order in self:
            super(SaleOrder, order)._amount_all()

            order.amount_untaxed -= order.global_discount_amount
            order.amount_total = order.amount_untaxed + order.amount_tax
