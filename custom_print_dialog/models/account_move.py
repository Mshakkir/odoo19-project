# -*- coding: utf-8 -*-
from odoo import models


# Map move_type to the Odoo standard report action external ID.
# The dialog JS will call /report/pdf/<report_name>/<record_id> for preview.
MOVE_TYPE_REPORT_MAP = {
    "out_invoice": "account.report_invoice_with_payments",
    "out_refund": "account.report_invoice",
    "out_receipt": "account.report_invoice",
    "in_invoice": "account.report_invoice_with_payments",
    "in_refund": "account.report_invoice",
    "in_receipt": "account.report_invoice",
    # Journal entries use the generic move report
    "entry": "account.report_move_template",
}

# Human-readable move type labels for the dialog title
MOVE_TYPE_LABEL = {
    "out_invoice": "Customer Invoice",
    "out_refund": "Credit Note",
    "out_receipt": "Sales Receipt",
    "in_invoice": "Vendor Bill",
    "in_refund": "Vendor Credit Note",
    "in_receipt": "Purchase Receipt",
    "entry": "Journal Entry",
}


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_custom_print_dialog(self):
        """
        Opens the custom print preview dialog for any move type.
        Passes the correct report reference so the dialog renders
        the right PDF (invoice, bill, receipt, or journal entry).
        """
        self.ensure_one()

        report_name = MOVE_TYPE_REPORT_MAP.get(self.move_type, "account.report_invoice")
        doc_label = MOVE_TYPE_LABEL.get(self.move_type, "Document")
        record_name = self.name or f"{doc_label}-{self.id}"

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
