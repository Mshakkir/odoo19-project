from odoo import models, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_invoice_line(self, **optional_values):
        """
        Override to ensure analytic_distribution is automatically
        propagated from Sales Order Line to Invoice Line
        """
        res = super()._prepare_invoice_line(**optional_values)

        # Automatically copy analytic_distribution from SO line to Invoice line
        if self.analytic_distribution:
            res['analytic_distribution'] = self.analytic_distribution

        return res