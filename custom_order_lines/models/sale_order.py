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

    @api.depends('product_uom_qty', 'price_unit', 'discount', 'price_subtotal', 'price_total')
    def _compute_tax_amount(self):
        for line in self:
            # Method 1: Use price_total and price_subtotal if available
            if hasattr(line, 'price_total') and hasattr(line, 'price_subtotal'):
                line.tax_amount = line.price_total - line.price_subtotal
            # Method 2: Calculate manually if we have tax fields
            elif 'tax_id' in line._fields and line.tax_id:
                try:
                    price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    taxes = line.tax_id.compute_all(
                        price,
                        line.order_id.currency_id,
                        line.product_uom_qty,
                        product=line.product_id,
                        partner=line.order_id.partner_shipping_id
                    )
                    line.tax_amount = sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                except:
                    line.tax_amount = 0.0
            else:
                line.tax_amount = 0.0

    @api.depends('untaxed_amount_after_discount', 'tax_amount')
    def _compute_total_amount(self):
        for line in self:
            line.total_amount = line.untaxed_amount_after_discount + line.tax_amount