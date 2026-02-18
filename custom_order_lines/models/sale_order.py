#
# from odoo import api, fields, models
#
#
# class SaleOrderLine(models.Model):
#     _inherit = 'sale.order.line'
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
#     untaxed_amount_after_discount = fields.Monetary(
#         string='Untax Amount',
#         compute='_compute_untaxed_amount_after_discount',
#         store=True
#     )
#
#     tax_amount = fields.Monetary(
#         string='Tax Value',
#         compute='_compute_tax_amount',
#         store=True
#     )
#
#     total_amount = fields.Monetary(
#         string='Total',
#         compute='_compute_total_amount',
#         store=True
#     )
#
#     is_stock_low = fields.Boolean(
#         string='Stock Low',
#         compute='_compute_is_stock_low',
#         store=False
#     )
#
#     @api.depends('product_id', 'product_id.qty_available', 'product_id.virtual_available')
#     def _compute_is_stock_low(self):
#         for line in self:
#             # Check if product exists and is a stockable product
#             # In Odoo 19, check product.type instead of detailed_type
#             if line.product_id and hasattr(line.product_id, 'type') and line.product_id.type == 'product':
#                 # Consider stock low if virtual available (forecasted) is <= 0
#                 line.is_stock_low = line.product_id.virtual_available <= 0
#             elif line.product_id and hasattr(line.product_id, 'detailed_type') and line.product_id.detailed_type == 'product':
#                 # Fallback for older versions
#                 line.is_stock_low = line.product_id.virtual_available <= 0
#             else:
#                 line.is_stock_low = False
#
#     @api.depends('order_id.order_line')
#     def _compute_sequence_number(self):
#         for order in self.mapped('order_id'):
#             number = 1
#             for line in order.order_line:
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
#     @api.depends('product_uom_qty', 'price_unit', 'discount')
#     def _compute_untaxed_amount_after_discount(self):
#         for line in self:
#             price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
#             line.untaxed_amount_after_discount = price * line.product_uom_qty
#
#     @api.depends('product_uom_qty', 'price_unit', 'discount', 'price_tax')
#     def _compute_tax_amount(self):
#         for line in self:
#             # Use the existing price_tax field which already contains the tax amount
#             line.tax_amount = line.price_tax if hasattr(line, 'price_tax') else 0.0
#
#     @api.depends('untaxed_amount_after_discount', 'tax_amount')
#     def _compute_total_amount(self):
#         for line in self:
#             line.total_amount = line.untaxed_amount_after_discount + line.tax_amount
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
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

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

    is_stock_low = fields.Boolean(
        string='Stock Low',
        compute='_compute_is_stock_low',
        store=False
    )

    def _get_warehouse_from_analytic(self):
        """
        Return the first warehouse whose name matches (ilike) any analytic
        account name selected on this line. Returns browse record or False.
        """
        _logger.debug(
            "[STOCK_CHECK][SO] line id=%s | product=%s | analytic_distribution=%s",
            self.id,
            self.product_id.display_name if self.product_id else 'None',
            self.analytic_distribution,
        )

        if not self.analytic_distribution:
            _logger.debug("[STOCK_CHECK][SO] analytic_distribution is empty/False")
            return False

        try:
            account_ids = [int(k) for k in self.analytic_distribution.keys()]
        except (ValueError, AttributeError) as e:
            _logger.warning("[STOCK_CHECK][SO] Failed to parse analytic_distribution: %s", e)
            return False

        accounts = self.env['account.analytic.account'].browse(account_ids).exists()
        _logger.debug(
            "[STOCK_CHECK][SO] Analytic accounts: %s",
            [(a.id, a.name) for a in accounts],
        )

        for account in accounts:
            # Search warehouse by name match
            warehouse = self.env['stock.warehouse'].search(
                [('name', 'ilike', account.name)], limit=1
            )
            _logger.debug(
                "[STOCK_CHECK][SO] Analytic '%s' → warehouse search result: %s",
                account.name,
                warehouse.name if warehouse else 'NOT FOUND',
            )
            if warehouse:
                return warehouse

        # Also try matching on short_name (e.g. 'JED') in case analytic = short code
        for account in accounts:
            warehouse = self.env['stock.warehouse'].search(
                [('short_name', 'ilike', account.name)], limit=1
            )
            _logger.debug(
                "[STOCK_CHECK][SO] Analytic '%s' → short_name search result: %s",
                account.name,
                warehouse.name if warehouse else 'NOT FOUND',
            )
            if warehouse:
                return warehouse

        _logger.debug("[STOCK_CHECK][SO] No matching warehouse found")
        return False

    @api.depends(
        'product_id',
        'product_id.qty_available',
        'product_id.virtual_available',
        'analytic_distribution',
    )
    def _compute_is_stock_low(self):
        StockQuant = self.env['stock.quant']
        for line in self:
            product = line.product_id
            _logger.debug(
                "[STOCK_CHECK][SO] Computing is_stock_low | line id=%s | product=%s",
                line.id,
                product.display_name if product else 'None',
            )

            if not product:
                line.is_stock_low = False
                continue

            product_type = getattr(product, 'type', None)
            detailed_type = getattr(product, 'detailed_type', None)
            is_storable = (product_type == 'product' or detailed_type == 'product')

            _logger.debug(
                "[STOCK_CHECK][SO] product.type=%s | product.detailed_type=%s | is_storable=%s",
                product_type, detailed_type, is_storable,
            )

            if not is_storable:
                line.is_stock_low = False
                continue

            warehouse = line._get_warehouse_from_analytic()

            if warehouse:
                location = warehouse.lot_stock_id
                quants = StockQuant.search([
                    ('product_id', '=', product.id),
                    ('location_id', 'child_of', location.id),
                ])
                on_hand = sum(quants.mapped('quantity'))
                reserved = sum(quants.mapped('reserved_quantity'))
                available = on_hand - reserved

                _logger.debug(
                    "[STOCK_CHECK][SO] Warehouse='%s' | Location='%s' | "
                    "on_hand=%.2f | reserved=%.2f | available=%.2f",
                    warehouse.name, location.complete_name,
                    on_hand, reserved, available,
                )

                line.is_stock_low = available <= 0
            else:
                # Fallback to global forecast
                _logger.debug(
                    "[STOCK_CHECK][SO] Fallback: virtual_available=%.2f",
                    product.virtual_available,
                )
                line.is_stock_low = product.virtual_available <= 0

            _logger.debug(
                "[STOCK_CHECK][SO] RESULT: is_stock_low=%s for product='%s'",
                line.is_stock_low,
                product.display_name,
            )

    @api.depends('order_id.order_line')
    def _compute_sequence_number(self):
        for order in self.mapped('order_id'):
            number = 1
            for line in order.order_line:
                line.sequence_number = number
                number += 1

    @api.depends('product_id', 'product_id.default_code')
    def _compute_product_code(self):
        for line in self:
            line.product_code = line.product_id.default_code if line.product_id else False

    def _search_product_code(self, operator, value):
        return [('product_id.default_code', operator, value)]

    @api.depends('product_uom_qty', 'price_unit', 'discount')
    def _compute_untaxed_amount_after_discount(self):
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            line.untaxed_amount_after_discount = price * line.product_uom_qty

    @api.depends('product_uom_qty', 'price_unit', 'discount', 'price_tax')
    def _compute_tax_amount(self):
        for line in self:
            line.tax_amount = line.price_tax if hasattr(line, 'price_tax') else 0.0

    @api.depends('untaxed_amount_after_discount', 'tax_amount')
    def _compute_total_amount(self):
        for line in self:
            line.total_amount = line.untaxed_amount_after_discount + line.tax_amount

    def action_product_forecast_report(self):
        self.ensure_one()
        if not self.product_id:
            return False
        try:
            action = self.env['ir.actions.act_window'].search(
                [('res_model', '=', 'report.stock.quantity')], limit=1
            )
            if action:
                result = action.read()[0]
                result['context'] = {
                    'search_default_product_id': self.product_id.id,
                    'default_product_id': self.product_id.id,
                }
                return result
        except Exception:
            pass
        try:
            action = self.env['ir.actions.act_window'].search(
                [('res_model', '=', 'stock.forecasted')], limit=1
            )
            if action:
                result = action.read()[0]
                result['context'] = {'search_default_product_id': self.product_id.id}
                return result
        except Exception:
            pass
        return {
            'name': self.product_id.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'res_id': self.product_id.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_detailed_type': 'product'},
        }