from odoo import models, fields, api
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_create_multi_invoice(self):
        """Open wizard to create invoice from multiple selected sale orders"""
        # Validate selection
        if not self:
            raise UserError("Please select at least one sale order!")

        # Check if all orders have the same customer
        partners = self.mapped('partner_id')
        if len(partners) > 1:
            raise UserError("All selected sale orders must have the same customer!")

        # Check if orders can be invoiced
        invalid_orders = self.filtered(lambda o: o.invoice_status not in ['to invoice', 'invoiced'])
        if invalid_orders:
            raise UserError(f"The following orders cannot be invoiced: {', '.join(invalid_orders.mapped('name'))}")

        return {
            'name': 'Create Invoice from Multiple Sale Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'multi.sale.invoice.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }