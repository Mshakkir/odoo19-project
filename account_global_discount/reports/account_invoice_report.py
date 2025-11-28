# Copyright 2019 Tecnativa - David Vidal
# Copyright 2025 - Odoo 19 CE Conversion
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.tools import SQL


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    @api.model
    def _where(self):
        """Include global discount lines in invoice report."""
        where_sql = super()._where()
        where_sql_str = where_sql.code.replace(
            "NOT line.exclude_from_invoice_tab",
            "(NOT line.exclude_from_invoice_tab OR line.invoice_global_discount_id IS NOT NULL)",
        )
        return SQL(where_sql_str)