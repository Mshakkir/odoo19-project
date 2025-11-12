from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    shipping_to = fields.Text(
        string='Shipping To',
        help='Shipping address details for this order'
    )

    def _prepare_invoice(self):
        """Pass shipping_to to invoice when creating from sale order"""
        invoice_vals = super()._prepare_invoice()
        invoice_vals['shipping_to'] = self.shipping_to
        return invoice_vals


class AccountMove(models.Model):
    _inherit = 'account.move'

    shipping_to = fields.Text(
        string='Shipping To',
        help='Shipping address details'
    )