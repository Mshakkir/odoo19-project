# -*- coding: utf-8 -*-
from odoo import models

PICKING_TYPE_LABEL = {
    "outgoing": "Delivery Order",
    "incoming": "Receipt",
    "internal": "Internal Transfer",
}


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def action_custom_print_dialog(self):
        """
        Opens the custom print preview dialog for a stock picking.

        report_action.xml overrides stock.action_report_delivery so that
        its report_name = 'stock.report_delivery_document' (custom template).

        Both assigned and done states use this same report.
        For picking operations (assigned), the same delivery document is used.
        """
        self.ensure_one()

        # Your report_action.xml sets stock.action_report_delivery
        # to use report_name = 'stock.report_delivery_document'
        # This is correct for both assigned (ready) and done states.
        report_name = "stock.report_delivery_document"

        doc_label   = PICKING_TYPE_LABEL.get(self.picking_type_code, "Transfer")
        record_name = self.name or f"Transfer-{self.id}"

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