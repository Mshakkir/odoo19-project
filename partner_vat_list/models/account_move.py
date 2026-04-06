from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.onchange('product_id')
    def _onchange_product_id_apply_partner_taxes(self):
        """
        After the standard product_id onchange sets product taxes,
        override with partner's VAT list based on move type:
          - Customer Invoice / Credit Note  → partner.sale_tax_ids
          - Vendor Bill / Refund            → partner.purchase_tax_ids
        """
        move = self.move_id
        if not move:
            return

        partner = move.partner_id
        if not partner:
            return

        commercial = partner.commercial_partner_id or partner
        company = move.company_id or self.env.company

        # Determine direction
        is_sale_move = move.move_type in ('out_invoice', 'out_refund')
        is_purchase_move = move.move_type in ('in_invoice', 'in_refund')

        if is_sale_move and commercial.sale_tax_ids:
            taxes = commercial.sale_tax_ids.filtered(
                lambda t: not t.company_id or t.company_id == company
            )
            self.tax_ids = taxes

        elif is_purchase_move and commercial.purchase_tax_ids:
            taxes = commercial.purchase_tax_ids.filtered(
                lambda t: not t.company_id or t.company_id == company
            )
            self.tax_ids = taxes
