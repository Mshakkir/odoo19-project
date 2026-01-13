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
        readonly=False,
        copy=False
    )

    @api.depends('invoice_origin', 'line_ids.sale_line_ids', 'line_ids.warehouse_id')
    def _compute_warehouse_id(self):
        """Get warehouse from invoice lines or related sale order"""
        for move in self:
            warehouse = False

            # Method 1: Get from invoice line warehouses (most direct)
            invoice_line_warehouses = move.line_ids.filtered(
                lambda l: l.display_type == 'product'
            ).mapped('warehouse_id')

            if invoice_line_warehouses:
                warehouse = invoice_line_warehouses[0]
                _logger.info(f"Invoice {move.name}: Found warehouse {warehouse.name} from invoice lines")

            # Method 2: From invoice lines -> sale order lines
            if not warehouse and move.line_ids:
                sale_lines = move.line_ids.mapped('sale_line_ids')
                if sale_lines:
                    sale_orders = sale_lines.mapped('order_id')
                    if sale_orders and sale_orders[0].warehouse_id:
                        warehouse = sale_orders[0].warehouse_id
                        _logger.info(f"Invoice {move.name}: Found warehouse {warehouse.name} from sale order")

            # Method 3: From invoice_origin (fallback)
            if not warehouse and move.invoice_origin:
                sale_order = self.env['sale.order'].search([
                    ('name', '=', move.invoice_origin)
                ], limit=1)
                if sale_order and sale_order.warehouse_id:
                    warehouse = sale_order.warehouse_id
                    _logger.info(f"Invoice {move.name}: Found warehouse {warehouse.name} from invoice_origin")

            if not warehouse:
                _logger.warning(f"Invoice {move.name}: No warehouse found")

            move.warehouse_id = warehouse

    def _recompute_all_warehouses(self):
        """Manual method to recompute all warehouses - run this once"""
        invoices = self.search([
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '!=', 'cancel')
        ])
        _logger.info(f"Starting warehouse recomputation for {len(invoices)} invoices...")

        count = 0
        for invoice in invoices:
            old_warehouse = invoice.warehouse_id
            invoice._compute_warehouse_id()
            if invoice.warehouse_id and invoice.warehouse_id != old_warehouse:
                count += 1
                _logger.info(f"  Updated {invoice.name}: {invoice.warehouse_id.name}")

        _logger.info(f"Warehouse recomputation complete! Updated {count} invoices.")
        return True