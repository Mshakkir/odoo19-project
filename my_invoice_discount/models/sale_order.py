from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    discount_amount = fields.Monetary(
        string="Discount",
        default=0.0,
        currency_field='currency_id',
    )
    freight_amount = fields.Monetary(
        string="Freight",
        default=0.0,
        currency_field='currency_id',
    )

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        invoice_vals.update({
            'discount_amount': self.discount_amount,
            'freight_amount': self.freight_amount,
        })
        return invoice_vals
