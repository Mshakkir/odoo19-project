from odoo import api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('partner_id')
    def _onchange_partner_id_apply_currency(self):
        """
        When the customer is changed on a Sale Order:
        - If the partner has a sale_currency_id configured, apply it as the order currency.
        - The existing custom_sale_order module's _onchange_currency_auto_fill_rate will
          then trigger automatically to populate the manual_currency_rate.

        NOTE: This onchange runs AFTER Odoo's built-in partner_id onchange on sale.order,
        so it safely overrides the currency that was set by the pricelist.
        """
        if not self.partner_id:
            return
        commercial = self.partner_id.commercial_partner_id or self.partner_id
        if commercial.sale_currency_id:
            # sale_currency_id is the field defined in the custom_sale_order module
            self.sale_currency_id = commercial.sale_currency_id
            self.currency_id = commercial.sale_currency_id


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

        commercial = partner.commercial_partner_id or partner

        if commercial.sale_tax_ids:
            company = self.order_id.company_id or self.env.company
            taxes = commercial.sale_tax_ids.filtered(
                lambda t: not t.company_id or t.company_id == company
            )
            self.tax_id = taxes
