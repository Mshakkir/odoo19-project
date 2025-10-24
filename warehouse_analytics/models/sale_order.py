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
            else:
                order.warehouse_analytic_id = False

    def _prepare_invoice(self):
        """
        When creating invoice from sales order, transfer warehouse analytic to invoice.
        ONLY transfer the warehouse_analytic_id field - do NOT touch analytic_distribution here.
        """
        invoice_vals = super(SaleOrder, self)._prepare_invoice()

        # ONLY set warehouse_analytic_id - the _post() method will handle the rest
        if self.warehouse_analytic_id:
            invoice_vals['warehouse_analytic_id'] = self.warehouse_analytic_id.id
            _logger.info(
                f"Invoice from SO {self.name}: Set warehouse analytic "
                f"'{self.warehouse_analytic_id.name}'"
            )

        return invoice_vals


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # DO NOT override _prepare_invoice_line - let it work normally
    # The analytic will be applied after invoice posting
    pass