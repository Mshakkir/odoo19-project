from odoo import models, api
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_create_invoice(self):
        """Override the standard create invoice action"""
        raise UserError(
            "❌ Invoice Creation via Sales Order is Disabled\n\n"
            "Your Odoo instance uses a CUSTOM INVOICE WORKFLOW.\n\n"
            "📋 PLEASE USE THIS WORKFLOW INSTEAD:\n"
            "1. Go to: Invoicing → Invoices\n"
            "2. Click: Create\n"
            "3. Select: Customer\n"
            "4. Choose: Sales Orders (you can select multiple)\n"
            "5. Invoice lines will populate AUTOMATICALLY\n\n"
            "✅ BENEFITS:\n"
            "• Combine multiple sales orders into ONE invoice\n"
            "• Automatic line item population\n"
            "• Better invoice management\n"
        )

    def action_view_invoice(self):
        """Keep the view invoices action working"""
        return super().action_view_invoice()

    @api.model
    def create(self, vals):
        """Allow normal creation"""
        return super().create(vals)

    def write(self, vals):
        """Allow normal updates"""
        return super().write(vals)