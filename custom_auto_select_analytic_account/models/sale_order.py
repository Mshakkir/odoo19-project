from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id')
    def _onchange_product_auto_copy_analytic(self):
        """
        Auto-copy analytic distribution from the first order line
        when adding new products
        """
        # Only proceed if this is a new line being added
        if self.product_id and not self.analytic_distribution and self.order_id:
            # Get existing order lines that have analytic distribution
            # Filter out the current line (which doesn't have an ID yet)
            existing_lines = self.order_id.order_line.filtered(
                lambda l: l.analytic_distribution and l.product_id
            )

            # If there are existing lines with analytic distribution
            if existing_lines:
                # Copy from the first line
                first_line = existing_lines[0]
                self.analytic_distribution = first_line.analytic_distribution.copy()

    @api.model_create_multi
    def create(self, vals_list):
        """
        Additional safety: Copy analytic distribution on line creation
        """
        lines = super().create(vals_list)

        for line in lines:
            # If line doesn't have analytic distribution
            if not line.analytic_distribution and line.order_id:
                # Get the first line with analytic distribution
                first_line = line.order_id.order_line.filtered(
                    lambda l: l.id != line.id and l.analytic_distribution
                )[:1]

                if first_line:
                    line.analytic_distribution = first_line.analytic_distribution.copy()

        return lines