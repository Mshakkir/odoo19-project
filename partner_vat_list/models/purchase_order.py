from odoo import api, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.onchange('product_id')
    def _onchange_product_id_apply_partner_taxes(self):
        """
        After the standard product_id onchange runs (which sets default product taxes),
        override the taxes_id field with the partner's configured Purchase VAT List if defined.
        """
        partner = self.order_id.partner_id
        if not partner:
            return

        commercial = partner.commercial_partner_id or partner

        if commercial.purchase_tax_ids:
            company = self.order_id.company_id or self.env.company
            taxes = commercial.purchase_tax_ids.filtered(
                lambda t: not t.company_id or t.company_id == company
            )
            self.tax_ids = taxes
