# from odoo import api, fields, models
#
#
# class PurchaseOrderLine(models.Model):
#     _inherit = 'purchase.order.line'
#
#     sequence_number = fields.Integer(
#         string='SN',
#         compute='_compute_sequence_number',
#         store=False
#     )
#
#     product_code = fields.Char(
#         string='P. Code',
#         related='product_id.default_code',
#         readonly=True
#     )
#
#     tax_amount = fields.Monetary(
#         string='Tax Value',
#         compute='_compute_tax_amount',
#         store=False,
#         currency_field='currency_id'
#     )
#
#     @api.depends('order_id.order_line', 'display_type')
#     def _compute_sequence_number(self):
#         for order in self.mapped('order_id'):
#             number = 1
#             # Only count lines with display_type 'product' or empty (regular lines)
#             for line in order.order_line.filtered(lambda l: l.display_type in ['product', False]):
#                 line.sequence_number = number
#                 number += 1
#
#     @api.depends('product_qty', 'price_unit', 'discount', 'tax_ids')
#     def _compute_tax_amount(self):
#         for line in self:
#             # Changed condition to include both 'product' and False display_type
#             if line.display_type in ['product', False] and line.tax_ids:
#                 try:
#                     # Calculate the base price after discount
#                     price_after_discount = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
#
#                     # Compute taxes on the base amount
#                     tax_results = line.tax_ids.compute_all(
#                         price_after_discount,
#                         line.order_id.currency_id,
#                         line.product_qty,
#                         product=line.product_id,
#                         partner=line.order_id.partner_id
#                     )
#
#                     # Extract tax amount from computation
#                     line.tax_amount = tax_results['total_included'] - tax_results['total_excluded']
#                 except Exception as e:
#                     # If tax computation fails, set to 0
#                     line.tax_amount = 0.0
#             else:
#                 line.tax_amount = 0.0
from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

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

    tax_amount = fields.Monetary(
        string='Tax Value',
        compute='_compute_tax_amount',
        store=False,
        currency_field='currency_id'
    )

    @api.depends('order_id.order_line', 'display_type')
    def _compute_sequence_number(self):
        for order in self.mapped('order_id'):
            number = 1
            # Only count lines with display_type 'product' or empty (regular lines)
            for line in order.order_line.filtered(lambda l: l.display_type in ['product', False]):
                line.sequence_number = number
                number += 1

    @api.depends('product_qty', 'price_unit', 'discount', 'tax_ids')
    def _compute_tax_amount(self):
        for line in self:
            # Changed condition to include both 'product' and False display_type
            if line.display_type in ['product', False] and line.tax_ids:
                try:
                    # Calculate the base price after discount
                    price_after_discount = line.price_unit * (1 - (line.discount or 0.0) / 100.0)

                    # Compute taxes on the base amount
                    tax_results = line.tax_ids.compute_all(
                        price_after_discount,
                        line.order_id.currency_id,
                        line.product_qty,
                        product=line.product_id,
                        partner=line.order_id.partner_id
                    )

                    # Extract tax amount from computation
                    line.tax_amount = tax_results['total_included'] - tax_results['total_excluded']
                except Exception as e:
                    # If tax computation fails, set to 0
                    line.tax_amount = 0.0
            else:
                line.tax_amount = 0.0

    def action_product_forecast_report(self):
        """Open the product's forecasted report"""
        self.ensure_one()
        if not self.product_id:
            return False

        # Call the product's action_product_forecast_report method
        return self.product_id.action_product_forecast_report()

