from odoo import models, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _prepare_account_move_line(self, move=False):
        """
        Override to ensure analytic_distribution is automatically
        propagated from Purchase Order Line to Bill Line
        """
        res = super()._prepare_account_move_line(move)

        # Automatically copy analytic_distribution from PO line to Bill line
        if self.analytic_distribution:
            res['analytic_distribution'] = self.analytic_distribution

        return res