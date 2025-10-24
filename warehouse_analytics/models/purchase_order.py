# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    warehouse_analytic_id = fields.Many2one(
        'account.analytic.account',
        string='Warehouse / Branch',
        compute='_compute_warehouse_analytic',
        store=True,
        readonly=False,
        tracking=True,
        help='Analytic account based on destination warehouse. Will be used in vendor bill.'
    )

    @api.depends('picking_type_id', 'picking_type_id.warehouse_id')
    def _compute_warehouse_analytic(self):
        """
        Auto-set warehouse analytic based on purchase order destination warehouse.
        """
        for order in self:
            warehouse = False

            # Try to get warehouse from picking type
            if order.picking_type_id and order.picking_type_id.warehouse_id:
                warehouse = order.picking_type_id.warehouse_id

            # Try to get from existing pickings
            elif order.picking_ids:
                warehouse = order.picking_ids[0].location_dest_id.warehouse_id

            if warehouse:
                # Find matching analytic account
                analytic = self.env['account.analytic.account'].search([
                    '|',
                    ('name', '=', warehouse.name),
                    ('name', 'ilike', warehouse.name),
                ], limit=1)

                if analytic:
                    order.warehouse_analytic_id = analytic
                    _logger.info(
                        f"PO {order.name}: Auto-set analytic '{analytic.name}' "
                        f"from warehouse '{warehouse.name}'"
                    )
                else:
                    order.warehouse_analytic_id = False
                    _logger.warning(
                        f"PO {order.name}: No analytic account found for warehouse "
                        f"'{warehouse.name}'. Please create one or set manually."
                    )
            else:
                order.warehouse_analytic_id = False

    def _prepare_invoice(self):
        """
        When creating vendor bill from purchase order, transfer warehouse analytic.
        """
        invoice_vals = super(PurchaseOrder, self)._prepare_invoice()

        # Add warehouse analytic to vendor bill
        if self.warehouse_analytic_id:
            invoice_vals['warehouse_analytic_id'] = self.warehouse_analytic_id.id
            _logger.info(
                f"Vendor bill from PO {self.name}: Set warehouse analytic "
                f"'{self.warehouse_analytic_id.name}'"
            )

        return invoice_vals

    def action_create_invoice(self):
        """
        Override invoice creation to ensure analytic is properly set.
        """
        result = super(PurchaseOrder, self).action_create_invoice()

        # If this opened an invoice form, we can't access the invoice object directly
        # The analytic will be set via _prepare_invoice()

        return result


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.depends('order_id.warehouse_analytic_id')
    def _compute_analytic_distribution(self):
        """
        Ensure purchase order lines inherit warehouse analytic from order header.
        """
        super(PurchaseOrderLine, self)._compute_analytic_distribution()

        for line in self:
            if line.order_id.warehouse_analytic_id and not line.analytic_distribution:
                line.analytic_distribution = {
                    str(line.order_id.warehouse_analytic_id.id): 100
                }