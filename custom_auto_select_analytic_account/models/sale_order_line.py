from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('analytic_distribution')
    def _onchange_analytic_distribution_set_warehouse(self):
        """
        Auto-select warehouse based on analytic account in analytic distribution.
        """
        if not self.analytic_distribution:
            return

        try:
            # Get the analytic account ID from distribution
            # analytic_distribution is a dict: {account_id: percentage}
            analytic_account_id = None
            max_percentage = 0

            for acc_id_str, percentage in self.analytic_distribution.items():
                if float(percentage) > max_percentage:
                    max_percentage = float(percentage)
                    analytic_account_id = int(acc_id_str)

            if analytic_account_id:
                # Get the analytic account record
                analytic_account = self.env['account.analytic.account'].browse(analytic_account_id)

                if analytic_account.exists() and analytic_account.name:
                    # Extract the warehouse name from analytic account name
                    # If your analytic account is "IWH-DAMMAM SS",
                    # and warehouse is "IWH-DAMMAM SS", they should match exactly
                    warehouse_name = analytic_account.name

                    # Search for warehouse with matching name
                    warehouse = self.env['stock.warehouse'].search([
                        ('name', '=', warehouse_name)
                    ], limit=1)

                    if warehouse:
                        # Update warehouse at order level
                        if self.order_id:
                            self.order_id.warehouse_id = warehouse.id
                            _logger.info(f"Warehouse changed to: {warehouse.name}")
                        return {
                            'value': {
                                'warehouse_id': warehouse.id
                            }
                        }
                    else:
                        _logger.warning(f"No warehouse found matching: {warehouse_name}")

        except Exception as e:
            _logger.error(f"Error in warehouse auto-selection: {str(e)}")


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('order_line', 'order_line.analytic_distribution')
    def _onchange_order_line_analytic_distribution(self):
        """
        Alternative approach: Monitor line changes and update warehouse at order level
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
                            warehouse = self.env['stock.warehouse'].search([
                                ('name', '=', analytic.name)
                            ], limit=1)

                            if warehouse and self.warehouse_id != warehouse:
                                self.warehouse_id = warehouse.id
                                return