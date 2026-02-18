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

    def _get_warehouse_from_analytic(self):
        """Return the first warehouse whose name matches an analytic account
        selected on this line. Returns a stock.warehouse record or False."""
        if not self.analytic_distribution:
            return False
        try:
            account_ids = [int(k) for k in self.analytic_distribution.keys()]
        except (ValueError, AttributeError):
            return False
        accounts = self.env['account.analytic.account'].browse(account_ids).exists()
        for account in accounts:
            warehouse = self.env['stock.warehouse'].search(
                [('name', 'ilike', account.name)], limit=1
            )
            if warehouse:
                return warehouse
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

            is_storable = (
                getattr(product, 'type', None) == 'product'
                or getattr(product, 'detailed_type', None) == 'product'
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
                qty = (
                    sum(quants.mapped('quantity'))
                    - sum(quants.mapped('reserved_quantity'))
                )
                line.is_stock_low = qty <= 0
            else:
                line.is_stock_low = product.virtual_available <= 0

    @api.depends('order_id.order_line', 'display_type')
    def _compute_sequence_number(self):
        for order in self.mapped('order_id'):
            number = 1
            for line in order.order_line.filtered(lambda l: l.display_type in ['product', False]):
                line.sequence_number = number
                number += 1

    @api.depends('product_id', 'product_id.default_code')
    def _compute_product_code(self):
        for line in self:
            line.product_code = line.product_id.default_code if line.product_id else False

    def _search_product_code(self, operator, value):
        return [('product_id.default_code', operator, value)]

    @api.depends('product_qty', 'price_unit', 'discount', 'tax_ids')
    def _compute_tax_amount(self):
        for line in self:
            if line.display_type in ['product', False] and line.tax_ids:
                try:
                    price_after_discount = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    tax_results = line.tax_ids.compute_all(
                        price_after_discount,
                        line.order_id.currency_id,
                        line.product_qty,
                        product=line.product_id,
                        partner=line.order_id.partner_id
                    )
                    line.tax_amount = tax_results['total_included'] - tax_results['total_excluded']
                except Exception:
                    line.tax_amount = 0.0
            else:
                line.tax_amount = 0.0

    def action_product_forecast_report(self):
        """Open the product's forecasted report"""
        self.ensure_one()
        if not self.product_id:
            return False

        try:
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
        except Exception:
            pass

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