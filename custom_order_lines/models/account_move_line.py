import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

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
        store=True,
        currency_field='currency_id'
    )

    is_stock_low = fields.Boolean(
        string='Stock Low',
        compute='_compute_is_stock_low',
        store=False
    )

    def _get_warehouse_from_analytic(self):
        if not self.analytic_distribution:
            _logger.info(
                "[STOCK_CHECK][INV] line id=%s product='%s' → NO analytic set",
                self.id,
                self.product_id.display_name if self.product_id else 'None',
            )
            return False

        try:
            account_ids = [int(k) for k in self.analytic_distribution.keys()]
        except (ValueError, AttributeError) as e:
            _logger.warning("[STOCK_CHECK][INV] Cannot parse analytic keys: %s", e)
            return False

        accounts = self.env['account.analytic.account'].browse(account_ids).exists()
        _logger.info(
            "[STOCK_CHECK][INV] line id=%s | analytic accounts: %s",
            self.id,
            [(a.id, a.name, a.code) for a in accounts],
        )

        Warehouse = self.env['stock.warehouse']
        # Odoo 16/17 uses 'short_name'; Odoo 18/19 renamed it to 'code'
        wh_code_field = 'code' if 'code' in Warehouse._fields else 'short_name'

        for account in accounts:
            for wh_field in ('name', wh_code_field):
                for analytic_val in (account.name, account.code):
                    if not analytic_val:
                        continue
                    wh = Warehouse.search([(wh_field, 'ilike', analytic_val)], limit=1)
                    _logger.info(
                        "[STOCK_CHECK][INV] warehouse.%s ilike '%s' → %s",
                        wh_field, analytic_val,
                        wh.name if wh else 'NOT FOUND',
                    )
                    if wh:
                        return wh

        _logger.info("[STOCK_CHECK][INV] No warehouse match for line id=%s", self.id)
        return False

    @api.depends(
        'product_id',
        'product_id.qty_available',
        'product_id.virtual_available',
        'analytic_distribution',
    )
    def _compute_is_stock_low(self):
        StockQuant = self.env['stock.quant']
        wh_code_field = 'code' if 'code' in self.env['stock.warehouse']._fields else 'short_name'

        for line in self:
            product = line.product_id

            if not product:
                line.is_stock_low = False
                continue

            product_type = getattr(product, 'type', None)
            detailed_type = getattr(product, 'detailed_type', None)

            _logger.info(
                "[STOCK_CHECK][INV] line id=%s | product='%s' | "
                "type=%s | detailed_type=%s | analytic=%s",
                line.id, product.display_name,
                product_type, detailed_type,
                line.analytic_distribution,
            )

            # Skip only pure services
            if product_type == 'service' or detailed_type == 'service':
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

                wh_code = getattr(warehouse, wh_code_field, '?')
                _logger.info(
                    "[STOCK_CHECK][INV] Warehouse='%s' code='%s' | "
                    "on_hand=%.2f | reserved=%.2f | available=%.2f",
                    warehouse.name, wh_code, on_hand, reserved, available,
                )
                line.is_stock_low = available <= 0
            else:
                _logger.info(
                    "[STOCK_CHECK][INV] Fallback: virtual_available=%.2f",
                    product.virtual_available,
                )
                line.is_stock_low = product.virtual_available <= 0

            _logger.info(
                "[STOCK_CHECK][INV] FINAL: product='%s' is_stock_low=%s",
                product.display_name, line.is_stock_low,
            )

    @api.onchange('product_id', 'analytic_distribution')
    def _onchange_recompute_stock_status(self):
        self._compute_is_stock_low()

    @api.depends('move_id.invoice_line_ids', 'display_type')
    def _compute_sequence_number(self):
        for line in self:
            if not line.move_id or not line.move_id.id:
                line.sequence_number = 0
                continue
            number = 1
            for invoice_line in line.move_id.invoice_line_ids.filtered(
                lambda l: l.display_type in ['product', False]
            ):
                if invoice_line.id == line.id:
                    line.sequence_number = number
                    break
                number += 1

    @api.depends('quantity', 'price_unit', 'discount', 'tax_ids', 'move_id.currency_id')
    def _compute_tax_amount(self):
        for line in self:
            if line.display_type == 'product' and line.tax_ids:
                price_after_discount = (
                    line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                )
                tax_results = line.tax_ids.compute_all(
                    price_after_discount,
                    line.move_id.currency_id,
                    line.quantity,
                    product=line.product_id,
                    partner=line.move_id.partner_id,
                )
                line.tax_amount = (
                    tax_results['total_included'] - tax_results['total_excluded']
                )
            else:
                line.tax_amount = 0.0

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
# from odoo import api, fields, models
#
#
# class AccountMoveLine(models.Model):
#     _inherit = 'account.move.line'
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
#         store=True,
#         currency_field='currency_id'
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
#     @api.depends('move_id.invoice_line_ids', 'display_type')
#     def _compute_sequence_number(self):
#         for line in self:
#             # Handle new records that don't have a move_id yet
#             if not line.move_id or not line.move_id.id:
#                 line.sequence_number = 0
#                 continue
#
#             number = 1
#             # Only count lines with display_type 'product' or empty (regular lines)
#             for invoice_line in line.move_id.invoice_line_ids.filtered(lambda l: l.display_type in ['product', False]):
#                 if invoice_line.id == line.id:
#                     line.sequence_number = number
#                     break
#                 number += 1
#
#     @api.depends('quantity', 'price_unit', 'discount', 'tax_ids', 'move_id.currency_id')
#     def _compute_tax_amount(self):
#         for line in self:
#             if line.display_type == 'product' and line.tax_ids:
#                 # Calculate the base price after discount
#                 price_after_discount = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
#                 base_amount = price_after_discount * line.quantity
#
#                 # Compute taxes on the base amount
#                 tax_results = line.tax_ids.compute_all(
#                     price_after_discount,
#                     line.move_id.currency_id,
#                     line.quantity,
#                     product=line.product_id,
#                     partner=line.move_id.partner_id
#                 )
#
#                 # Extract tax amount from computation
#                 line.tax_amount = tax_results['total_included'] - tax_results['total_excluded']
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