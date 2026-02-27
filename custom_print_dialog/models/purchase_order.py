# -*- coding: utf-8 -*-
from odoo import models

# Human-readable labels per purchase order state
PURCHASE_STATE_LABEL = {
    "draft": "Request for Quotation",
    "sent": "RFQ Sent",
    "to approve": "Purchase Order (Pending Approval)",
    "purchase": "Purchase Order",
    "cancel": "Cancelled",
}


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def action_custom_print_dialog(self):
        """
        Opens the custom print preview dialog for a purchase order / RFQ.

        Two original buttons are replaced:
          - print_quotation (type=object) — draft / sent / to approve states
            → uses report: purchase.report_purchasequotation
          - action 870 (type=action)      — purchase (confirmed) state
            → uses report: purchase.report_purchaseorder

        We pick the correct report based on state so the right
        document template is always shown in the preview.
        """
        self.ensure_one()

        if self.state == "purchase":
            # Confirmed Purchase Order report
            report_name = "purchase.report_purchaseorder"
        else:
            # Request for Quotation report (draft / sent / to approve)
            report_name = "purchase.report_purchasequotation"

        doc_label = PURCHASE_STATE_LABEL.get(self.state, "Purchase Order")
        record_name = self.name or f"PO-{self.id}"

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
