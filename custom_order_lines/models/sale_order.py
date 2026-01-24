from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    sequence_number = fields.Integer(
        string='SN',
        compute='_compute_sequence_number',
        store=False
    )

    product_code = fields.Char(
        string='P. Code',
        related='product_id.default_code',
        readonly=True
    )

    untaxed_amount_after_discount = fields.Monetary(
        string='Untax Amount',
        compute='_compute_untaxed_amount_after_discount',
        store=True
    )

    tax_amount = fields.Monetary(
        string='Tax Value',
        compute='_compute_tax_amount',
        store=True
    )

    total_amount = fields.Monetary(
        string='Total',
        compute='_compute_total_amount',
        store=True
    )

    @api.depends('order_id.order_line')
    def _compute_sequence_number(self):
        for order in self.mapped('order_id'):
            number = 1
            for line in order.order_line:
                line.sequence_number = number
                number += 1

    @api.depends('product_uom_qty', 'price_unit', 'discount')
    def _compute_untaxed_amount_after_discount(self):
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            line.untaxed_amount_after_discount = price * line.product_uom_qty

    @api.depends('product_uom_qty', 'price_unit', 'discount', 'price_tax')
    def _compute_tax_amount(self):
        for line in self:
            # Use the existing price_tax field which already contains the tax amount
            line.tax_amount = line.price_tax if hasattr(line, 'price_tax') else 0.0

    @api.depends('untaxed_amount_after_discount', 'tax_amount')
    def _compute_total_amount(self):
        for line in self:
            line.total_amount = line.untaxed_amount_after_discount + line.tax_amount
