from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    discount_type = fields.Selection([
        ('amount', 'Fixed Amount'),
        ('percent', 'Percentage'),
    ], string="Discount Type", default='amount')

    discount_value = fields.Float(string="Discount Value", default=0.0)
    freight_amount = fields.Monetary(
        string="Freight",
        default=0.0,
        currency_field='currency_id',
    )
    total_discount = fields.Monetary(
        string="Discount",
        compute="_compute_total_discount",
        store=True,
        currency_field='currency_id'
    )

    @api.depends('discount_type', 'discount_value', 'amount_untaxed')
    def _compute_total_discount(self):
        for order in self:
            if order.discount_type == 'percent':
                order.total_discount = (order.amount_untaxed * order.discount_value) / 100
            else:
                order.total_discount = order.discount_value

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        invoice_vals.update({
            'discount_type': self.discount_type,
            'discount_value': self.discount_value,
            'total_discount': self.total_discount,
            'freight_amount': self.freight_amount,
        })
        return invoice_vals

    custom_untaxed_amount = fields.Monetary(
        compute="_compute_custom_totals",
        store=True,
        currency_field='currency_id'
    )
    custom_gross_total = fields.Monetary(
        compute="_compute_custom_totals",
        store=True,
        currency_field='currency_id'
    )
    custom_tax_amount = fields.Monetary(
        compute="_compute_custom_totals",
        store=True,
        currency_field='currency_id'
    )
    custom_net_total = fields.Monetary(
        compute="_compute_custom_totals",
        store=True,
        currency_field='currency_id'
    )

    @api.depends('amount_untaxed', 'freight_amount', 'total_discount', 'order_line')
    def _compute_custom_totals(self):
        for order in self:
            order.custom_untaxed_amount = order.amount_untaxed
            gross = order.amount_untaxed - order.total_discount + order.freight_amount
            order.custom_gross_total = gross
            order.custom_tax_amount = gross * self._get_tax_rate(order)
            order.custom_net_total = gross + order.custom_tax_amount

    def _get_tax_rate(self, order):
        taxes = order.order_line.mapped('tax_ids').filtered(lambda t: t)
        if taxes:
            # Example: take the first tax rate
            return taxes[0].amount / 100.0
        return 0.0

