from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    shipping_to = fields.Text(
        string='Shipping To',
        help='Shipping address details for this order'
    )

    shipping_currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        help='Currency for this order',
        default=lambda self: self.env.company.currency_id
    )

    @api.onchange('shipping_currency_id')
    def _onchange_shipping_currency(self):
        """Update the order currency when shipping currency changes"""
        if self.shipping_currency_id:
            self.currency_id = self.shipping_currency_id
            # Recalculate prices for all order lines
            for line in self.order_line:
                line._compute_amount()

    def _prepare_invoice(self):
        """Pass shipping info to invoice"""
        invoice_vals = super()._prepare_invoice()
        invoice_vals['shipping_to'] = self.shipping_to
        invoice_vals['shipping_currency_id'] = self.shipping_currency_id.id if self.shipping_currency_id else False
        return invoice_vals


class AccountMove(models.Model):
    _inherit = 'account.move'

    shipping_to = fields.Text(
        string='Shipping To',
        help='Shipping address details'
    )

    shipping_currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        help='Currency for this invoice'
    )




# from odoo import models, fields, api

# class SaleOrder(models.Model):
#     _inherit = 'sale.order'
#
#     shipping_to = fields.Text(
#         string='Shipping To',
#         help='Shipping address details for this order'
#     )
#
#     def _prepare_invoice(self):
#         """Pass shipping_to to invoice when creating from sale order"""
#         invoice_vals = super()._prepare_invoice()
#         invoice_vals['shipping_to'] = self.shipping_to
#         return invoice_vals
#
#
# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#     shipping_to = fields.Text(
#         string='Shipping To',
#         help='Shipping address details'
#     )