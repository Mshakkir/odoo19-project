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

    # -------------------------------------------------------------------------
    # Warehouse-user helpers
    # -------------------------------------------------------------------------

    def _get_user_default_analytic_and_warehouse(self):
        """
        Return (analytic_account, warehouse) that belong to the current user.

        Strategy (in order):
        1. User's employee → analytic account set on the employee.
        2. User's analytic account via res.users field (if exists).
        3. Analytic account whose name/code matches a warehouse name/code
           that the current user is a *stock user* of (warehouse-level groups
           are not standard, so we fall back to matching by name).

        Returns (account_id|False, warehouse|False).
        """
        user = self.env.user
        account = self.env['account.analytic.account']
        warehouse = self.env['stock.warehouse']

        # -- 1. Employee analytic account
        if hasattr(user, 'employee_id') and user.employee_id:
            emp = user.employee_id
            if hasattr(emp, 'analytic_account_id') and emp.analytic_account_id:
                account = emp.analytic_account_id

        # -- 2. Direct field on res.users (custom or OCA)
        if not account and hasattr(user, 'analytic_account_id') and user.analytic_account_id:
            account = user.analytic_account_id

        # -- 3. Match analytic account by user's warehouse company
        #    Find warehouses accessible to the user's company.
        #    If only one warehouse exists and no account found, skip auto-fill.
        if account:
            # Try to find matching warehouse for the account we have
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
        If the current user has a default analytic account / warehouse,
        set analytic_distribution and (for SO) the warehouse on the parent order.
        Called from onchange so it only fires in the UI.
        """
        account, warehouse = self._get_user_default_analytic_and_warehouse()

        if account and not self.analytic_distribution:
            self.analytic_distribution = {str(account.id): 100}
            _logger.info(
                "[USER_DEFAULT][SO] line id=%s → analytic set to '%s'",
                self.id, account.name,
            )

        # Set the delivery warehouse on the parent sale order if not yet set
        if warehouse and self.order_id and hasattr(self.order_id, 'warehouse_id'):
            if not self.order_id.warehouse_id or self.order_id.warehouse_id == self.env['stock.warehouse']:
                self.order_id.warehouse_id = warehouse
                _logger.info(
                    "[USER_DEFAULT][SO] order id=%s → warehouse set to '%s'",
                    self.order_id.id, warehouse.name,
                )

    # -------------------------------------------------------------------------
    # Onchange – auto-fill when product is selected or line is created
    # -------------------------------------------------------------------------

    @api.onchange('product_id')
    def _onchange_product_apply_user_defaults(self):
        if self.product_id:
            self._apply_user_defaults()

    # -------------------------------------------------------------------------
    # Also apply defaults on new lines created programmatically (e.g. copy)
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if not record.analytic_distribution:
                account, warehouse = record._get_user_default_analytic_and_warehouse()
                if account:
                    record.analytic_distribution = {str(account.id): 100}
                if warehouse and record.order_id and hasattr(record.order_id, 'warehouse_id'):
                    if not record.order_id.warehouse_id:
                        record.order_id.warehouse_id = warehouse
        return records

    # -------------------------------------------------------------------------
    # Warehouse helper (stock check)
    # -------------------------------------------------------------------------

    def _get_warehouse_from_analytic(self):
        """
        Match warehouse from analytic account on this line.
        Tries warehouse.name and warehouse.code (Odoo 19, was short_name)
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
        wh_code_field = 'code' if 'code' in Warehouse._fields else 'short_name'

        for account in accounts:
            for wh_field in ('name', wh_code_field):
                for analytic_val in (account.name, account.code):
                    if not analytic_val:
                        continue
                    wh = Warehouse.search([(wh_field, 'ilike', analytic_val)], limit=1)
                    _logger.info(
                        "[STOCK_CHECK][SO] warehouse.%s ilike '%s' → %s",
                        wh_field, analytic_val,
                        wh.name if wh else 'NOT FOUND',
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
        wh_code_field = 'code' if 'code' in self.env['stock.warehouse']._fields else 'short_name'

        for line in self:
            product = line.product_id

            if not product:
                line.is_stock_low = False
                continue

            product_type = getattr(product, 'type', None)
            detailed_type = getattr(product, 'detailed_type', None)

            _logger.info(
                "[STOCK_CHECK][SO] line id=%s | product='%s' | "
                "type=%s | detailed_type=%s | analytic=%s",
                line.id, product.display_name,
                product_type, detailed_type,
                line.analytic_distribution,
            )

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

                wh_code = getattr(warehouse, wh_code_field, '?')
                _logger.info(
                    "[STOCK_CHECK][SO] Warehouse='%s' code='%s' | "
                    "on_hand=%.2f | reserved=%.2f | available=%.2f",
                    warehouse.name, wh_code,
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










# import logging
# from odoo import api, fields, models
#
# _logger = logging.getLogger(__name__)
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
#     def _get_warehouse_from_analytic(self):
#         """
#         Match warehouse from analytic account on this line.
#         Tries warehouse.name and warehouse.code (Odoo 19, was short_name)
#         against both account.name and account.code.
#         """
#         if not self.analytic_distribution:
#             _logger.info(
#                 "[STOCK_CHECK][SO] line id=%s product='%s' → NO analytic set",
#                 self.id,
#                 self.product_id.display_name if self.product_id else 'None',
#             )
#             return False
#
#         try:
#             account_ids = [int(k) for k in self.analytic_distribution.keys()]
#         except (ValueError, AttributeError) as e:
#             _logger.warning("[STOCK_CHECK][SO] Cannot parse analytic keys: %s", e)
#             return False
#
#         accounts = self.env['account.analytic.account'].browse(account_ids).exists()
#         _logger.info(
#             "[STOCK_CHECK][SO] line id=%s | analytic accounts: %s",
#             self.id,
#             [(a.id, a.name, a.code) for a in accounts],
#         )
#
#         Warehouse = self.env['stock.warehouse']
#
#         # Determine the correct warehouse code field name
#         # Odoo 16/17 uses 'short_name', Odoo 18/19 renamed it to 'code'
#         wh_code_field = 'code' if 'code' in self.env['stock.warehouse']._fields else 'short_name'
#
#         for account in accounts:
#             for wh_field in ('name', wh_code_field):
#                 for analytic_val in (account.name, account.code):
#                     if not analytic_val:
#                         continue
#                     wh = Warehouse.search([(wh_field, 'ilike', analytic_val)], limit=1)
#                     _logger.info(
#                         "[STOCK_CHECK][SO] warehouse.%s ilike '%s' → %s",
#                         wh_field, analytic_val,
#                         wh.name if wh else 'NOT FOUND',
#                     )
#                     if wh:
#                         return wh
#
#         _logger.info("[STOCK_CHECK][SO] No warehouse match for line id=%s", self.id)
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
#         # Determine warehouse code field once per call
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
#                 "[STOCK_CHECK][SO] line id=%s | product='%s' | "
#                 "type=%s | detailed_type=%s | analytic=%s",
#                 line.id, product.display_name,
#                 product_type, detailed_type,
#                 line.analytic_distribution,
#             )
#
#             # Skip only pure service products
#             if product_type == 'service' or detailed_type == 'service':
#                 line.is_stock_low = False
#                 _logger.info(
#                     "[STOCK_CHECK][SO] product='%s' is a service → skip",
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
#                     "[STOCK_CHECK][SO] Warehouse='%s' code='%s' | "
#                     "on_hand=%.2f | reserved=%.2f | available=%.2f",
#                     warehouse.name, wh_code,
#                     on_hand, reserved, available,
#                 )
#                 line.is_stock_low = available <= 0
#             else:
#                 _logger.info(
#                     "[STOCK_CHECK][SO] Fallback: virtual_available=%.2f",
#                     product.virtual_available,
#                 )
#                 line.is_stock_low = product.virtual_available <= 0
#
#             _logger.info(
#                 "[STOCK_CHECK][SO] FINAL: product='%s' is_stock_low=%s",
#                 product.display_name, line.is_stock_low,
#             )
#
#     @api.onchange('product_id', 'analytic_distribution')
#     def _onchange_recompute_stock_status(self):
#         self._compute_is_stock_low()
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
#             line.product_code = (
#                 line.product_id.default_code if line.product_id else False
#             )
#
#     def _search_product_code(self, operator, value):
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
#             line.tax_amount = line.price_tax if hasattr(line, 'price_tax') else 0.0
#
#     @api.depends('untaxed_amount_after_discount', 'tax_amount')
#     def _compute_total_amount(self):
#         for line in self:
#             line.total_amount = (
#                 line.untaxed_amount_after_discount + line.tax_amount
#             )
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