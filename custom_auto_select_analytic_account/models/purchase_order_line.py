from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.onchange('analytic_distribution')
    def _onchange_analytic_distribution_set_picking_type(self):
        """
        Auto-select picking type (operation type) based on analytic account
        in analytic distribution for purchase order lines.
        """
        if not self.analytic_distribution:
            return

        try:
            # Get the analytic account with highest percentage
            max_percentage = 0
            main_analytic_id = None

            for acc_id_str, percentage in self.analytic_distribution.items():
                if float(percentage) > max_percentage:
                    max_percentage = float(percentage)
                    main_analytic_id = int(acc_id_str)

            if main_analytic_id:
                # Get the analytic account record
                analytic_account = self.env['account.analytic.account'].browse(main_analytic_id)

                if analytic_account.exists() and analytic_account.name:
                    warehouse_name = analytic_account.name

                    # Search for warehouse with matching name
                    warehouse = self.env['stock.warehouse'].search([
                        ('name', '=', warehouse_name),
                        '|',
                        ('company_id', '=', self.order_id.company_id.id),
                        ('company_id', '=', False)
                    ], limit=1)

                    if warehouse:
                        # Get the incoming picking type (Receipts) for this warehouse
                        picking_type = self.env['stock.picking.type'].search([
                            ('warehouse_id', '=', warehouse.id),
                            ('code', '=', 'incoming')  # Incoming = Receipts
                        ], limit=1)

                        if picking_type:
                            # Update picking type on the purchase order
                            self.order_id.picking_type_id = picking_type.id
                            _logger.info(
                                f"Picking type '{picking_type.name}' for warehouse '{warehouse.name}' "
                                f"auto-selected based on analytic account '{analytic_account.name}'"
                            )
                        else:
                            _logger.warning(
                                f"No incoming picking type found for warehouse '{warehouse_name}'"
                            )
                    else:
                        _logger.warning(
                            f"No warehouse found with name '{warehouse_name}' "
                            f"matching analytic account"
                        )

        except Exception as e:
            _logger.error(f"Error in auto-selecting picking type: {str(e)}")


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.onchange('order_line', 'order_line.analytic_distribution')
    def _onchange_order_line_analytic_distribution(self):
        """
        Monitor line changes and update picking type at order level
        """
        if self.order_line:
            for line in self.order_line:
                if line.analytic_distribution:
                    # Get first/main analytic account
                    analytic_ids = list(line.analytic_distribution.keys())
                    if analytic_ids:
                        analytic_id = int(analytic_ids[0])
                        analytic = self.env['account.analytic.account'].browse(analytic_id)

                        if analytic.exists() and analytic.name:
                            # Find warehouse
                            warehouse = self.env['stock.warehouse'].search([
                                ('name', '=', analytic.name)
                            ], limit=1)

                            if warehouse:
                                # Get incoming picking type
                                picking_type = self.env['stock.picking.type'].search([
                                    ('warehouse_id', '=', warehouse.id),
                                    ('code', '=', 'incoming')
                                ], limit=1)

                                if picking_type and self.picking_type_id != picking_type:
                                    self.picking_type_id = picking_type.id
                                    return

