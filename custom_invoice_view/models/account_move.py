from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        compute='_compute_warehouse_id',
        store=True,
        readonly=True,
        copy=False
    )

    @api.depends('line_ids.sale_line_ids.order_id.warehouse_id')
    def _compute_warehouse_id(self):
        """Get warehouse from the related sale order"""
        for move in self:
            warehouse = False

            # Get warehouse from invoice lines linked to sale order lines
            sale_orders = move.line_ids.sale_line_ids.order_id
            if sale_orders:
                # Take the first sale order's warehouse
                warehouse = sale_orders[0].warehouse_id

            move.warehouse_id = warehouse


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # This ensures the link to sale order lines exists
    # It should already exist in Odoo, but we make it explicit
    sale_line_ids = fields.Many2many(
        'sale.order.line',
        'sale_order_line_invoice_rel',
        'invoice_line_id',
        'order_line_id',
        string='Sales Order Lines',
        readonly=True,
        copy=False
    )