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
#         compute='_compute_product_code',
#         store=True,
#         search='_search_product_code',
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
#     @api.depends('product_id', 'product_id.default_code')
#     def _compute_product_code(self):
#         for line in self:
#             line.product_code = line.product_id.default_code if line.product_id else False
#
#     def _search_product_code(self, operator, value):
#         """Enable search on product_code field by searching on product's default_code"""
#         return [('product_id.default_code', operator, value)]
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
#
#     def action_product_forecast_report(self):
#         """Open the product's forecasted report"""
#         self.ensure_one()
#         if not self.product_id:
#             return False
#
#         # Try different methods to open the forecast report
#         # Method 1: Try to find and use the stock forecasted report action
#         try:
#             # Look for the report.stock.quantity action or similar
#             action = self.env['ir.actions.act_window'].search([
#                 ('res_model', '=', 'report.stock.quantity'),
#             ], limit=1)
#
#             if action:
#                 result = action.read()[0]
#                 result['context'] = {
#                     'search_default_product_id': self.product_id.id,
#                     'default_product_id': self.product_id.id,
#                 }
#                 return result
#         except:
#             pass
#
#         # Method 2: Try stock.quantitative.forecasted
#         try:
#             action = self.env['ir.actions.act_window'].search([
#                 ('res_model', '=', 'stock.forecasted'),
#             ], limit=1)
#
#             if action:
#                 result = action.read()[0]
#                 result['context'] = {
#                     'search_default_product_id': self.product_id.id,
#                 }
#                 return result
#         except:
#             pass
#
#         # Method 3: Open product form and let user click replenish manually
#         return {
#             'name': self.product_id.display_name,
#             'type': 'ir.actions.act_window',
#             'res_model': 'product.product',
#             'res_id': self.product_id.id,
#             'view_mode': 'form',
#             'target': 'current',
#             'context': {
#                 'default_detailed_type': 'product',
#             }
#         }
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
        compute='_compute_product_code',
        store=True,
        search='_search_product_code',
        readonly=True
    )

    tax_amount = fields.Monetary(
        string='Tax Value',
        compute='_compute_tax_amount',
        store=False,
        currency_field='currency_id'
    )

    is_stock_low = fields.Boolean(
        string='Stock Low',
        compute='_compute_is_stock_low',
        store=False
    )

    @api.depends('product_id', 'product_id.qty_available', 'product_id.virtual_available')
    def _compute_is_stock_low(self):
        for line in self:
            if line.product_id and line.product_id.detailed_type == 'product':
                # Consider stock low if virtual available (forecasted) is <= 0
                line.is_stock_low = line.product_id.virtual_available <= 0
            else:
                line.is_stock_low = False

    @api.depends('order_id.order_line', 'display_type')
    def _compute_sequence_number(self):
        for order in self.mapped('order_id'):
            number = 1
            # Only count lines with display_type 'product' or empty (regular lines)
            for line in order.order_line.filtered(lambda l: l.display_type in ['product', False]):
                line.sequence_number = number
                number += 1

    @api.depends('product_id', 'product_id.default_code')
    def _compute_product_code(self):
        for line in self:
            line.product_code = line.product_id.default_code if line.product_id else False

    def _search_product_code(self, operator, value):
        """Enable search on product_code field by searching on product's default_code"""
        return [('product_id.default_code', operator, value)]

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

        # Try different methods to open the forecast report
        # Method 1: Try to find and use the stock forecasted report action
        try:
            # Look for the report.stock.quantity action or similar
            action = self.env['ir.actions.act_window'].search([
                ('res_model', '=', 'report.stock.quantity'),
            ], limit=1)

            if action:
                result = action.read()[0]
                result['context'] = {
                    'search_default_product_id': self.product_id.id,
                    'default_product_id': self.product_id.id,
                }
                return result
        except:
            pass

        # Method 2: Try stock.quantitative.forecasted
        try:
            action = self.env['ir.actions.act_window'].search([
                ('res_model', '=', 'stock.forecasted'),
            ], limit=1)

            if action:
                result = action.read()[0]
                result['context'] = {
                    'search_default_product_id': self.product_id.id,
                }
                return result
        except:
            pass

        # Method 3: Open product form and let user click replenish manually
        return {
            'name': self.product_id.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'res_id': self.product_id.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_detailed_type': 'product',
            }
        }