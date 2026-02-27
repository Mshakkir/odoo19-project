# -*- coding: utf-8 -*-
from odoo import models

# Map sale order state to human-readable label
SALE_STATE_LABEL = {
    "draft": "Quotation",
    "sent": "Quotation Sent",
    "sale": "Sales Order",
    "cancel": "Cancelled Order",
}


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_custom_print_dialog(self):
        """
        Opens the custom print preview dialog for a sale order / quotation.
        Uses the standard Odoo sale order report.
        """
        self.ensure_one()

        # Standard sale order report — works for both quotations and confirmed orders
        report_name = "sale.report_saleorder"

        doc_label = SALE_STATE_LABEL.get(self.state, "Sales Order")
        record_name = self.name or f"Order-{self.id}"

        return {
            "type": "ir.actions.client",
            "tag": "custom_print_dialog.open_print_dialog",
            "params": {
                "record_id": self.id,
                "record_name": record_name,
                "report_name": report_name,
                "doc_label": doc_label,
            },
        }
