from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_global_discount = fields.Boolean(default=False)


class AccountMove(models.Model):
    _inherit = "account.move"

    global_discount_fixed = fields.Monetary(
        string="Global Discount (Fixed)",
        currency_field="currency_id",
        default=0.0,
    )

    def _recompute_dynamic_lines(self, recompute_all_taxes=False,
                                 recompute_tax_base_amount=False):
        """Ensure invoice line generation keeps discount tax logic."""
        super()._recompute_dynamic_lines(
            recompute_all_taxes=recompute_all_taxes,
            recompute_tax_base_amount=recompute_tax_base_amount
        )
