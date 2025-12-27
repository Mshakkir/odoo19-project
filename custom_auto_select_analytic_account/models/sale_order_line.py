from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('analytic_distribution')
    def _onchange_analytic_distribution_set_warehouse(self):
        """
        Auto-select warehouse based on analytic account in analytic distribution
        """
        if self.analytic_distribution:
            # Get the first analytic account from distribution
            # analytic_distribution is a dict like {account_id: percentage}
            analytic_account_ids = [int(acc_id) for acc_id in self.analytic_distribution.keys()]

            if analytic_account_ids:
                # Get the analytic account with highest percentage or first one
                main_analytic_id = analytic_account_ids[0]
                analytic_account = self.env['account.analytic.account'].browse(main_analytic_id)

                if analytic_account and analytic_account.name:
                    # Search for warehouse with same name
                    warehouse = self.env['stock.warehouse'].search([
                        ('name', '=', analytic_account.name)
                    ], limit=1)

                    if warehouse:
                        # Update the warehouse on the order line
                        self.order_id.warehouse_id = warehouse.id