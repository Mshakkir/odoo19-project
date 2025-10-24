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
        help='Analytic account based on warehouse. Will be used in invoice.'
    )

    @api.depends('warehouse_id')
    def _compute_warehouse_analytic(self):
        """
        Auto-set warehouse analytic based on sales order warehouse.
        Matches warehouse name with analytic account name.
        """
        for order in self:
            if order.warehouse_id:
                # Try to find analytic account matching warehouse name
                analytic = self.env['account.analytic.account'].search([
                    '|',
                    ('name', '=', order.warehouse_id.name),
                    ('name', 'ilike', order.warehouse_id.name),
                ], limit=1)

                if analytic:
                    order.warehouse_analytic_id = analytic
                    _logger.info(
                        f"SO {order.name}: Auto-set analytic '{analytic.name}' "
                        f"from warehouse '{order.warehouse_id.name}'"
                    )
                else:
                    order.warehouse_analytic_id = False
                    _logger.warning(
                        f"SO {order.name}: No analytic account found for warehouse "
                        f"'{order.warehouse_id.name}'. Please create one or set manually."
                    )
            else:
                order.warehouse_analytic_id = False

    def _prepare_invoice(self):
        """
        When creating invoice from sales order, transfer warehouse analytic to invoice.
        This ensures invoice automatically gets the correct warehouse.
        """
        invoice_vals = super(SaleOrder, self)._prepare_invoice()

        # Add warehouse analytic to invoice
        if self.warehouse_analytic_id:
            invoice_vals['warehouse_analytic_id'] = self.warehouse_analytic_id.id
            _logger.info(
                f"Invoice from SO {self.name}: Set warehouse analytic "
                f"'{self.warehouse_analytic_id.name}'"
            )

        return invoice_vals

    def _create_invoices(self, grouped=False, final=False, date=None):
        """
        Override invoice creation to ensure analytic is properly set.
        """
        invoices = super(SaleOrder, self)._create_invoices(grouped, final, date)

        # After invoices are created, ensure warehouse analytic is set
        for invoice in invoices:
            # Get all related sale orders for this invoice
            sale_orders = invoice.invoice_line_ids.mapped('sale_line_ids.order_id')

            if not sale_orders:
                continue

            # If invoice doesn't have warehouse analytic but sale orders do, apply it
            if not invoice.warehouse_analytic_id:
                # Get unique warehouse analytics from all related sale orders
                warehouse_analytics = sale_orders.mapped('warehouse_analytic_id')

                # If all sale orders have the same warehouse analytic, apply to invoice
                if len(set(warehouse_analytics.ids)) == 1 and warehouse_analytics:
                    invoice.warehouse_analytic_id = warehouse_analytics[0]

                    # Also update all invoice lines to have this analytic
                    analytic_distribution = {str(warehouse_analytics[0].id): 100}
                    for line in invoice.invoice_line_ids.filtered(lambda l: not l.display_type):
                        if not line.analytic_distribution:
                            line.analytic_distribution = analytic_distribution

                    _logger.info(
                        f"Invoice {invoice.name}: Applied warehouse analytic "
                        f"'{warehouse_analytics[0].name}' from sales orders"
                    )

        return invoices


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('order_id.warehouse_analytic_id')
    def _compute_analytic_distribution(self):
        """
        Ensure sale order lines inherit warehouse analytic from order header.
        """
        super(SaleOrderLine, self)._compute_analytic_distribution()

        for line in self:
            if line.order_id.warehouse_analytic_id and not line.analytic_distribution:
                line.analytic_distribution = {
                    str(line.order_id.warehouse_analytic_id.id): 100
                }