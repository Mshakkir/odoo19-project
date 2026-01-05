from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id')
    def _onchange_product_id_copy_analytic(self):
        """
        Auto-copy analytic distribution from the first order line
        when adding new products
        """
        res = super()._onchange_product_id_copy_analytic()

        # Only proceed if this is a new line (no ID yet)
        if not self.id and self.order_id:
            # Get existing order lines that have analytic distribution
            existing_lines = self.order_id.order_line.filtered(
                lambda l: l.id and l.analytic_distribution
            )

            # If there are existing lines with analytic distribution
            if existing_lines:
                # Copy from the first line
                first_line = existing_lines[0]
                self.analytic_distribution = first_line.analytic_distribution

        return res


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _create_order_line(self, vals):
        """
        Alternative approach: Copy analytic distribution when creating new lines
        """
        line = super()._create_order_line(vals)

        # If the new line doesn't have analytic distribution
        if line and not vals.get('analytic_distribution'):
            # Get the first line with analytic distribution
            first_line = self.order_line.filtered(
                lambda l: l.id != line.id and l.analytic_distribution
            )[:1]

            if first_line:
                line.analytic_distribution = first_line.analytic_distribution

        return line