# -*- coding: utf-8 -*-
from odoo import models

PAYMENT_TYPE_LABEL = {
    "inbound":  "Customer Receipt",
    "outbound": "Vendor Payment",
    "transfer": "Internal Transfer",
}


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_custom_print_dialog(self):
        """
        Opens the custom print preview dialog for a payment receipt.
        Uses the standard Odoo payment receipt report.
        Only available when state is 'in_process' or 'paid' (i.e. confirmed).
        """
        self.ensure_one()
        report_name = "account.report_payment_receipt"
        doc_label   = PAYMENT_TYPE_LABEL.get(self.payment_type, "Payment Receipt")
        record_name = self.name or f"Payment-{self.id}"

        return {
            "type": "ir.actions.client",
            "tag":  "custom_print_dialog.open_print_dialog",
            "params": {
                "record_id":   self.id,
                "record_name": record_name,
                "report_name": report_name,
                "doc_label":   doc_label,
            },
        }