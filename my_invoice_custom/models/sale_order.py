from odoo import models, fields

class AccountMove(models.Model):
    _inherit = "account.move"

    discount = fields.Float(string="Discount")

class SaleOrder(models.Model):
    _inherit = "sale.order"

    discount = fields.Float(string="Discount")

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals['discount'] = self.discount
        return invoice_vals