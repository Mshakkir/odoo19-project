import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


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

    # -------------------------------------------------------------------------
    # Warehouse-user helpers
    # -------------------------------------------------------------------------

    def _get_user_default_analytic_and_warehouse(self):
        """
        Return (analytic_account, warehouse) belonging to the current user.
        See sale_order.py for full strategy documentation.
        """
        user = self.env.user
        account = self.env['account.analytic.account']
        warehouse = self.env['stock.warehouse']

        # 1. Employee analytic account
        if hasattr(user, 'employee_id') and user.employee_id:
            emp = user.employee_id
            if hasattr(emp, 'analytic_account_id') and emp.analytic_account_id:
                account = emp.analytic_account_id

        # 2. Direct field on res.users
        if not account and hasattr(user, 'analytic_account_id') and user.analytic_account_id:
            account = user.analytic_account_id

        # 3. Match warehouse from the analytic account found
        if account:
            Warehouse = self.env['stock.warehouse']
            wh_code_field = 'code' if 'code' in Warehouse._fields else 'short_name'
            for wh_field in ('name', wh_code_field):
                for analytic_val in (account.name, account.code):
                    if not analytic_val:
                        continue
                    wh = Warehouse.search([
                        (wh_field, 'ilike', analytic_val),
                        ('company_id', '=', user.company_id.id),
                    ], limit=1)
                    if wh:
                        warehouse = wh
                        break
                if warehouse:
                    break

        return account, warehouse

    def _apply_user_defaults(self):
        """
        Set analytic_distribution and destination warehouse (picking_type_id)
        from the current user's defaults if not already set.
        """
        account, warehouse = self._get_user_default_analytic_and_warehouse()

        if account and not self.analytic_distribution:
            self.analytic_distribution = {str(account.id): 100}
            _logger.info(
                "[USER_DEFAULT][PO] line id=%s → analytic set to '%s'",
                self.id, account.name,
            )

        # For PO, the destination warehouse is driven by order_id.picking_type_id
        if warehouse and self.order_id:
            # picking_type_id links to a warehouse via warehouse_id
            current_wh = (
                self.order_id.picking_type_id.warehouse_id
                if self.order_id.picking_type_id else False
            )
            if not current_wh or current_wh.id != warehouse.id:
                # Find the "Receipts" operation type for this warehouse
                receipt_type = self.env['stock.picking.type'].search([
                    ('warehouse_id', '=', warehouse.id),
                    ('code', '=', 'incoming'),
                ], limit=1)
                if receipt_type:
                    self.order_id.picking_type_id = receipt_type
                    _logger.info(
                        "[USER_DEFAULT][PO] order id=%s → picking_type set to '%s' (warehouse '%s')",
                        self.order_id.id, receipt_type.name, warehouse.name,
                    )

    # -------------------------------------------------------------------------
    # Onchange – auto-fill when product is selected
    # -------------------------------------------------------------------------

    @api.onchange('product_id')
    def _onchange_product_apply_user_defaults(self):
        if self.product_id:
            self._apply_user_defaults()

    # -------------------------------------------------------------------------
    # Also apply defaults on programmatic creation
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if not record.analytic_distribution:
                account, warehouse = record._get_user_default_analytic_and_warehouse()
                if account:
                    record.analytic_distribution = {str(account.id): 100}
                if warehouse and record.order_id:
                    current_wh = (
                        record.order_id.picking_type_id.warehouse_id
                        if record.order_id.picking_type_id else False
                    )
                    if not current_wh or current_wh.id != warehouse.id:
                        receipt_type = self.env['stock.picking.type'].search([
                            ('warehouse_id', '=', warehouse.id),
                            ('code', '=', 'incoming'),
                        ], limit=1)
                        if receipt_type:
                            record.order_id.picking_type_id = receipt_type
        return records

    # -------------------------------------------------------------------------
    # Warehouse helper (stock check)
    # -------------------------------------------------------------------------

    def _get_warehouse_from_analytic(self):
        if not self.analytic_distribution:
            _logger.info(
                "[STOCK_CHECK][PO] line id=%s product='%s' → NO analytic set",
                self.id,
                self.product_id.display_name if self.product_id else 'None',
            )
            return False

        try:
            account_ids = [int(k) for k in self.analytic_distribution.keys()]
        except (ValueError, AttributeError) as e:
            _logger.warning("[STOCK_CHECK][PO] Cannot parse analytic keys: %s", e)
            return False

        accounts = self.env['account.analytic.account'].browse(account_ids).exists()
        _logger.info(
            "[STOCK_CHECK][PO] line id=%s | analytic accounts: %s",
            self.id,
            [(a.id, a.name, a.code) for a in accounts],
        )

        Warehouse = self.env['stock.warehouse']
        wh_code_field = 'code' if 'code' in Warehouse._fields else 'short_name'

        for account in accounts:
            for wh_field in ('name', wh_code_field):
                for analytic_val in (account.name, account.code):
                    if not analytic_val:
                        continue
                    wh = Warehouse.search([(wh_field, 'ilike', analytic_val)], limit=1)
                    _logger.info(
                        "[STOCK_CHECK][PO] warehouse.%s ilike '%s' → %s",
                        wh_field, analytic_val,
                        wh.name if wh else 'NOT FOUND',
                    )
                    if wh:
                        return wh

        _logger.info("[STOCK_CHECK][PO] No warehouse match for line id=%s", self.id)
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
                "[STOCK_CHECK][PO] line id=%s | product='%s' | "
                "type=%s | detailed_type=%s | analytic=%s",
                line.id, product.display_name,
                product_type, detailed_type,
                line.analytic_distribution,
            )

            if product_type == 'service' or detailed_type == 'service':
                line.is_stock_low = False
                _logger.info(
                    "[STOCK_CHECK][PO] product='%s' is a service → skip",
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

                wh_code = getattr(warehouse, wh_code_field, '?')
                _logger.info(
                    "[STOCK_CHECK][PO] Warehouse='%s' code='%s' | "
                    "on_hand=%.2f | reserved=%.2f | available=%.2f",
                    warehouse.name, wh_code,
                    on_hand, reserved, available,
                )
                line.is_stock_low = available <= 0
            else:
                _logger.info(
                    "[STOCK_CHECK][PO] Fallback: virtual_available=%.2f",
                    product.virtual_available,
                )
                line.is_stock_low = product.virtual_available <= 0

            _logger.info(
                "[STOCK_CHECK][PO] FINAL: product='%s' is_stock_low=%s",
                product.display_name, line.is_stock_low,
            )

    @api.onchange('product_id', 'analytic_distribution')
    def _onchange_recompute_stock_status(self):
        self._compute_is_stock_low()

    @api.depends('order_id.order_line', 'display_type')
    def _compute_sequence_number(self):
        for order in self.mapped('order_id'):
            number = 1
            for line in order.order_line.filtered(
                lambda l: l.display_type in ['product', False]
            ):
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

    @api.depends('product_qty', 'price_unit', 'discount', 'tax_ids')
    def _compute_tax_amount(self):
        for line in self:
            if line.display_type in ['product', False] and line.tax_ids:
                try:
                    price_after_discount = (
                        line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    )
                    tax_results = line.tax_ids.compute_all(
                        price_after_discount,
                        line.order_id.currency_id,
                        line.product_qty,
                        product=line.product_id,
                        partner=line.order_id.partner_id,
                    )
                    line.tax_amount = (
                        tax_results['total_included'] - tax_results['total_excluded']
                    )
                except Exception:
                    line.tax_amount = 0.0
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


















# import logging
# from odoo import api, fields, models
#
# _logger = logging.getLogger(__name__)
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
#     is_stock_low = fields.Boolean(
#         string='Stock Low',
#         compute='_compute_is_stock_low',
#         store=False
#     )
#
#     def _get_warehouse_from_analytic(self):
#         if not self.analytic_distribution:
#             _logger.info(
#                 "[STOCK_CHECK][PO] line id=%s product='%s' → NO analytic set",
#                 self.id,
#                 self.product_id.display_name if self.product_id else 'None',
#             )
#             return False
#
#         try:
#             account_ids = [int(k) for k in self.analytic_distribution.keys()]
#         except (ValueError, AttributeError) as e:
#             _logger.warning("[STOCK_CHECK][PO] Cannot parse analytic keys: %s", e)
#             return False
#
#         accounts = self.env['account.analytic.account'].browse(account_ids).exists()
#         _logger.info(
#             "[STOCK_CHECK][PO] line id=%s | analytic accounts: %s",
#             self.id,
#             [(a.id, a.name, a.code) for a in accounts],
#         )
#
#         Warehouse = self.env['stock.warehouse']
#         wh_code_field = 'code' if 'code' in Warehouse._fields else 'short_name'
#
#         for account in accounts:
#             for wh_field in ('name', wh_code_field):
#                 for analytic_val in (account.name, account.code):
#                     if not analytic_val:
#                         continue
#                     wh = Warehouse.search([(wh_field, 'ilike', analytic_val)], limit=1)
#                     _logger.info(
#                         "[STOCK_CHECK][PO] warehouse.%s ilike '%s' → %s",
#                         wh_field, analytic_val,
#                         wh.name if wh else 'NOT FOUND',
#                     )
#                     if wh:
#                         return wh
#
#         _logger.info("[STOCK_CHECK][PO] No warehouse match for line id=%s", self.id)
#         return False
#
#     @api.depends(
#         'product_id',
#         'product_id.qty_available',
#         'product_id.virtual_available',
#         'analytic_distribution',
#     )
#     def _compute_is_stock_low(self):
#         StockQuant = self.env['stock.quant']
#         wh_code_field = 'code' if 'code' in self.env['stock.warehouse']._fields else 'short_name'
#
#         for line in self:
#             product = line.product_id
#
#             if not product:
#                 line.is_stock_low = False
#                 continue
#
#             product_type = getattr(product, 'type', None)
#             detailed_type = getattr(product, 'detailed_type', None)
#
#             _logger.info(
#                 "[STOCK_CHECK][PO] line id=%s | product='%s' | "
#                 "type=%s | detailed_type=%s | analytic=%s",
#                 line.id, product.display_name,
#                 product_type, detailed_type,
#                 line.analytic_distribution,
#             )
#
#             if product_type == 'service' or detailed_type == 'service':
#                 line.is_stock_low = False
#                 _logger.info(
#                     "[STOCK_CHECK][PO] product='%s' is a service → skip",
#                     product.display_name,
#                 )
#                 continue
#
#             warehouse = line._get_warehouse_from_analytic()
#
#             if warehouse:
#                 location = warehouse.lot_stock_id
#                 quants = StockQuant.search([
#                     ('product_id', '=', product.id),
#                     ('location_id', 'child_of', location.id),
#                 ])
#                 on_hand = sum(quants.mapped('quantity'))
#                 reserved = sum(quants.mapped('reserved_quantity'))
#                 available = on_hand - reserved
#
#                 wh_code = getattr(warehouse, wh_code_field, '?')
#                 _logger.info(
#                     "[STOCK_CHECK][PO] Warehouse='%s' code='%s' | "
#                     "on_hand=%.2f | reserved=%.2f | available=%.2f",
#                     warehouse.name, wh_code,
#                     on_hand, reserved, available,
#                 )
#                 line.is_stock_low = available <= 0
#             else:
#                 _logger.info(
#                     "[STOCK_CHECK][PO] Fallback: virtual_available=%.2f",
#                     product.virtual_available,
#                 )
#                 line.is_stock_low = product.virtual_available <= 0
#
#             _logger.info(
#                 "[STOCK_CHECK][PO] FINAL: product='%s' is_stock_low=%s",
#                 product.display_name, line.is_stock_low,
#             )
#
#     @api.onchange('product_id', 'analytic_distribution')
#     def _onchange_recompute_stock_status(self):
#         self._compute_is_stock_low()
#
#     @api.depends('order_id.order_line', 'display_type')
#     def _compute_sequence_number(self):
#         for order in self.mapped('order_id'):
#             number = 1
#             for line in order.order_line.filtered(
#                 lambda l: l.display_type in ['product', False]
#             ):
#                 line.sequence_number = number
#                 number += 1
#
#     @api.depends('product_id', 'product_id.default_code')
#     def _compute_product_code(self):
#         for line in self:
#             line.product_code = (
#                 line.product_id.default_code if line.product_id else False
#             )
#
#     def _search_product_code(self, operator, value):
#         return [('product_id.default_code', operator, value)]
#
#     @api.depends('product_qty', 'price_unit', 'discount', 'tax_ids')
#     def _compute_tax_amount(self):
#         for line in self:
#             if line.display_type in ['product', False] and line.tax_ids:
#                 try:
#                     price_after_discount = (
#                         line.price_unit * (1 - (line.discount or 0.0) / 100.0)
#                     )
#                     tax_results = line.tax_ids.compute_all(
#                         price_after_discount,
#                         line.order_id.currency_id,
#                         line.product_qty,
#                         product=line.product_id,
#                         partner=line.order_id.partner_id,
#                     )
#                     line.tax_amount = (
#                         tax_results['total_included'] - tax_results['total_excluded']
#                     )
#                 except Exception:
#                     line.tax_amount = 0.0
#             else:
#                 line.tax_amount = 0.0
#
#     def action_product_forecast_report(self):
#         self.ensure_one()
#         if not self.product_id:
#             return False
#         try:
#             action = self.env['ir.actions.act_window'].search(
#                 [('res_model', '=', 'report.stock.quantity')], limit=1
#             )
#             if action:
#                 result = action.read()[0]
#                 result['context'] = {
#                     'search_default_product_id': self.product_id.id,
#                     'default_product_id': self.product_id.id,
#                 }
#                 return result
#         except Exception:
#             pass
#         try:
#             action = self.env['ir.actions.act_window'].search(
#                 [('res_model', '=', 'stock.forecasted')], limit=1
#             )
#             if action:
#                 result = action.read()[0]
#                 result['context'] = {
#                     'search_default_product_id': self.product_id.id,
#                 }
#                 return result
#         except Exception:
#             pass
#         return {
#             'name': self.product_id.display_name,
#             'type': 'ir.actions.act_window',
#             'res_model': 'product.product',
#             'res_id': self.product_id.id,
#             'view_mode': 'form',
#             'target': 'current',
#             'context': {'default_detailed_type': 'product'},
#         }