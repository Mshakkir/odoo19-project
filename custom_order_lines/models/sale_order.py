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
        Match warehouse from analytic account on this line.
        Tries matching warehouse.name and warehouse.short_name
        against both account.name and account.code.
        """
        if not self.analytic_distribution:
            _logger.info(
                "[STOCK_CHECK][SO] line id=%s product='%s' → NO analytic set",
                self.id,
                self.product_id.display_name if self.product_id else 'None',
            )
            return False

        try:
            account_ids = [int(k) for k in self.analytic_distribution.keys()]
        except (ValueError, AttributeError) as e:
            _logger.warning("[STOCK_CHECK][SO] Cannot parse analytic keys: %s", e)
            return False

        accounts = self.env['account.analytic.account'].browse(account_ids).exists()
        _logger.info(
            "[STOCK_CHECK][SO] line id=%s | analytic accounts: %s",
            self.id,
            [(a.id, a.name, a.code) for a in accounts],
        )

        Warehouse = self.env['stock.warehouse']
        for account in accounts:
            for field in ('name', 'short_name'):
                for attr in (account.name, account.code):
                    if not attr:
                        continue
                    wh = Warehouse.search([(field, 'ilike', attr)], limit=1)
                    _logger.info(
                        "[STOCK_CHECK][SO] warehouse.%s ilike '%s' → %s",
                        field, attr, wh.name if wh else 'NOT FOUND',
                    )
                    if wh:
                        return wh

        _logger.info("[STOCK_CHECK][SO] No warehouse match for line id=%s", self.id)
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

            if not product:
                line.is_stock_low = False
                continue

            # -------------------------------------------------------
            # Odoo 17/18/19 changed product types:
            #   type='service'  → no stock, skip
            #   type='consu'    → consumable OR storable (check quants)
            #   type='product'  → storable (older Odoo versions)
            # We skip ONLY pure service products.
            # -------------------------------------------------------
            product_type = getattr(product, 'type', None)
            detailed_type = getattr(product, 'detailed_type', None)

            _logger.info(
                "[STOCK_CHECK][SO] line id=%s | product='%s' | "
                "type=%s | detailed_type=%s | analytic=%s",
                line.id, product.display_name,
                product_type, detailed_type,
                line.analytic_distribution,
            )

            # Skip only services
            if product_type == 'service' or detailed_type == 'service':
                line.is_stock_low = False
                _logger.info(
                    "[STOCK_CHECK][SO] product='%s' is a service → skip",
                    product.display_name,
                )
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

                _logger.info(
                    "[STOCK_CHECK][SO] Warehouse='%s' short='%s' | "
                    "on_hand=%.2f | reserved=%.2f | available=%.2f",
                    warehouse.name, warehouse.short_name,
                    on_hand, reserved, available,
                )
                line.is_stock_low = available <= 0
            else:
                _logger.info(
                    "[STOCK_CHECK][SO] Fallback: virtual_available=%.2f",
                    product.virtual_available,
                )
                line.is_stock_low = product.virtual_available <= 0

            _logger.info(
                "[STOCK_CHECK][SO] FINAL: product='%s' is_stock_low=%s",
                product.display_name, line.is_stock_low,
            )

    @api.onchange('product_id', 'analytic_distribution')
    def _onchange_recompute_stock_status(self):
        self._compute_is_stock_low()

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
            line.product_code = (
                line.product_id.default_code if line.product_id else False
            )

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
            line.total_amount = (
                line.untaxed_amount_after_discount + line.tax_amount
            )

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
                result['context'] = {
                    'search_default_product_id': self.product_id.id,
                }
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