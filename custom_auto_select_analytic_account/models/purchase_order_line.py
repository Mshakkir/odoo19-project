from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.onchange('analytic_distribution')
    def _onchange_analytic_distribution_set_destination(self):
        """
        Auto-select destination location (Deliver To) based on analytic account
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
                    location_name = analytic_account.name

                    # Search for stock location with matching name
                    # Looking for locations of type 'internal' (warehouse locations)
                    location = self.env['stock.location'].search([
                        ('name', '=', location_name),
                        ('usage', '=', 'internal'),
                        '|',
                        ('company_id', '=', self.order_id.company_id.id),
                        ('company_id', '=', False)
                    ], limit=1)

                    if location:
                        # Update destination location on the purchase order
                        self.order_id.dest_address_id = location.id
                        _logger.info(
                            f"Delivery location '{location.name}' auto-selected based on "
                            f"analytic account '{analytic_account.name}'"
                        )
                    else:
                        # If no location found, try finding by warehouse
                        warehouse = self.env['stock.warehouse'].search([
                            ('name', '=', location_name)
                        ], limit=1)

                        if warehouse and warehouse.lot_stock_id:
                            # Use warehouse's main stock location
                            self.order_id.dest_address_id = warehouse.lot_stock_id.id
                            _logger.info(
                                f"Warehouse location '{warehouse.name}' auto-selected based on "
                                f"analytic account '{analytic_account.name}'"
                            )
                        else:
                            _logger.warning(
                                f"No location or warehouse found with name '{location_name}' "
                                f"matching analytic account"
                            )

        except Exception as e:
            _logger.error(f"Error in auto-selecting delivery location: {str(e)}")


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.onchange('order_line', 'order_line.analytic_distribution')
    def _onchange_order_line_analytic_distribution(self):
        """
        Monitor line changes and update delivery location at order level
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
                            # Try to find location first
                            location = self.env['stock.location'].search([
                                ('name', '=', analytic.name),
                                ('usage', '=', 'internal')
                            ], limit=1)

                            if not location:
                                # Try warehouse
                                warehouse = self.env['stock.warehouse'].search([
                                    ('name', '=', analytic.name)
                                ], limit=1)
                                if warehouse:
                                    location = warehouse.lot_stock_id

                            if location and self.dest_address_id != location:
                                self.dest_address_id = location.id
                                return