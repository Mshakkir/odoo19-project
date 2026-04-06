from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id')
    def _onchange_product_id_apply_partner_taxes(self):
        """
        After the standard product_id onchange runs (which sets default product taxes),
        override the tax_id field with the partner's configured Sales VAT List if defined.
        """
        partner = self.order_id.partner_id
        if not partner:
            return

        # Resolve commercial partner (the one that holds the tax configuration)
        commercial = partner.commercial_partner_id or partner

        if commercial.sale_tax_ids:
            # Filter taxes by company to be safe
            company = self.order_id.company_id or self.env.company
            taxes = commercial.sale_tax_ids.filtered(
                lambda t: not t.company_id or t.company_id == company
            )
            self.tax_id = taxes
