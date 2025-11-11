# from odoo import models, fields
#
# class AccountMove(models.Model):
#     _inherit = "account.move"
#
#     discount = fields.Float(string="Discount")
#
# class SaleOrder(models.Model):
#     _inherit = "sale.order"
#
#     def _prepare_invoice(self):
#         invoice_vals = super()._prepare_invoice()
#         invoice_vals['discount'] = self.discount
#         return invoice_vals


from odoo import models, fields



class AccountMove(models.Model):
    _inherit = "account.move"

    discount = fields.Float(string="Discount")

    def amount_to_text_arabic(self, amount):
        """Convert amount to Arabic words"""
        try:
            # Use Odoo's built-in method with Arabic context
            return self.currency_id.with_context(lang='ar_001').amount_to_text(amount)
        except Exception as e:
            # Fallback to default if Arabic conversion fails
            return self.currency_id.amount_to_text(amount)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        invoice_vals['discount'] = self.discount
        return invoice_vals