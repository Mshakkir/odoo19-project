from odoo import models, fields, api
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def action_create_invoice(self):
        """
        Override the create invoice action to redirect users to use the custom invoice module.
        This prevents the standard Odoo invoice creation and guides them to the proper workflow.
        """
        raise UserError(
            "Invoice Creation via Sales Order is Disabled\n\n"
            "Please use the custom 'Invoice Sales Order Link' workflow instead:\n\n"
            "1. Go to Invoicing → Invoices\n"
            "2. Click 'Create'\n"
            "3. Select your customer\n"
            "4. Choose one or multiple sales orders from the 'Sales Orders' field\n"
            "5. Invoice lines will be populated automatically\n\n"
            "This allows you to combine multiple sales orders into a single invoice."
        )

    def action_view_invoice(self):
        """Override to show related invoices"""
        return super().action_view_invoice()