# -*- coding: utf-8 -*-
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)

_WAREHOUSE_FIELDS = ('property_warehouse_id', 'default_warehouse_id', 'warehouse_id')


def _get_user_warehouse(user):
    for fname in _WAREHOUSE_FIELDS:
        if fname in user._fields:
            return getattr(user, fname, False)
    return False


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _get_warehouse_analytic_account(self):
        wh = _get_user_warehouse(self.env.user)
        if wh and wh.analytic_account_id:
            return wh.analytic_account_id
        return False

    def _apply_warehouse_analytic_to_lines(self):
        """Stamp warehouse analytic on all purchase order lines."""
        analytic_account = self._get_warehouse_analytic_account()
        if not analytic_account:
            return
        key = str(analytic_account.id)
        for order in self:
            for line in order.order_line.filtered(lambda l: not l.display_type):
                existing = line.analytic_distribution or {}
                if key not in existing:
                    new_dist = dict(existing)
                    new_dist[key] = 100.0
                    line.analytic_distribution = new_dist
                    _logger.debug(
                        'Warehouse analytic %s applied to purchase line %s',
                        analytic_account.name, line.id,
                    )

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders._apply_warehouse_analytic_to_lines()
        return orders

    def write(self, vals):
        result = super().write(vals)
        if 'order_line' in vals:
            self._apply_warehouse_analytic_to_lines()
        return result

    def button_confirm(self):
        """Re-apply on confirmation (RFQ → purchase order)."""
        self._apply_warehouse_analytic_to_lines()
        return super().button_confirm()


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines.order_id._apply_warehouse_analytic_to_lines()
        return lines

    def write(self, vals):
        result = super().write(vals)
        if any(k in vals for k in ('product_id', 'analytic_distribution')):
            self.order_id._apply_warehouse_analytic_to_lines()
        return result

    @api.onchange('product_id')
    def _onchange_product_apply_warehouse_analytic(self):
        wh = _get_user_warehouse(self.env.user)
        if not wh or not wh.analytic_account_id:
            return
        key = str(wh.analytic_account_id.id)
        existing = self.analytic_distribution or {}
        if key not in existing:
            new_dist = dict(existing)
            new_dist[key] = 100.0
            self.analytic_distribution = new_dist
