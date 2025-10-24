# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    warehouse_analytic_id = fields.Many2one(
        'account.analytic.account',
        string='Warehouse / Branch',
        compute='_compute_warehouse_analytic',
        store=True,
        readonly=False,
        tracking=True,
        copy=False,
        help='Analytic account based on warehouse. Will be used in invoice.'
    )

    @api.depends('warehouse_id')
    def _compute_warehouse_analytic(self):
        """
        Auto-set warehouse analytic based on sales order warehouse.
        """
        for order in self:
            if order.warehouse_id:
                warehouse_name = order.warehouse_id.name

                analytic = self.env['account.analytic.account'].search([
                    '|',
                    ('name', '=', warehouse_name),
                    ('name', 'ilike', warehouse_name),
                ], limit=1)

                if analytic:
                    order.warehouse_analytic_id = analytic
                    _logger.info(f"✓ SO: Auto-set analytic '{analytic.name}' from warehouse '{warehouse_name}'")
                else:
                    order.warehouse_analytic_id = False
            else:
                order.warehouse_analytic_id = False

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        """
        Additional onchange trigger.
        """
        if self.warehouse_id:
            self._compute_warehouse_analytic()

    def _prepare_invoice(self):
        """
        Transfer ONLY warehouse_analytic_id to invoice.
        Do NOT touch analytic_distribution at all.
        """
        invoice_vals = super(SaleOrder, self)._prepare_invoice()

        if self.warehouse_analytic_id:
            invoice_vals['warehouse_analytic_id'] = self.warehouse_analytic_id.id
            _logger.info(f"✓ Invoice prep: warehouse_analytic_id = {self.warehouse_analytic_id.id}")

        return invoice_vals

    def _create_invoices(self, grouped=False, final=False, date=None):
        """
        Override to apply analytics AFTER invoice creation.
        """
        # Create invoices normally WITHOUT any analytic manipulation
        invoices = super(SaleOrder, self)._create_invoices(grouped, final, date)

        # NOW apply warehouse analytic to the created invoices
        for invoice in invoices:
            sale_orders = invoice.invoice_line_ids.mapped('sale_line_ids.order_id')

            if not sale_orders:
                continue

            # Get warehouse analytics from sale orders
            warehouse_analytics = sale_orders.mapped('warehouse_analytic_id').filtered(lambda x: x)

            if warehouse_analytics and len(set(warehouse_analytics.ids)) == 1:
                # All sale orders have same warehouse analytic
                if not invoice.warehouse_analytic_id:
                    invoice.warehouse_analytic_id = warehouse_analytics[0]
                    _logger.info(f"✓ Invoice {invoice.name}: Set warehouse_analytic_id = {warehouse_analytics[0].name}")

        return invoices


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_invoice_line(self, **optional_values):
        """
        CRITICAL: Remove analytic_distribution from invoice line preparation.
        This prevents the NoneType error during invoice creation.
        """
        res = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)

        # FORCE remove analytic_distribution if it exists
        if 'analytic_distribution' in res:
            del res['analytic_distribution']
            _logger.info("Removed analytic_distribution from invoice line to prevent creation error")

        # Also check for analytic_account_id (old field)
        if 'analytic_account_id' in res:
            del res['analytic_account_id']

        return res