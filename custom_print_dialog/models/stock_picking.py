# -*- coding: utf-8 -*-
from odoo import models

# Labels per picking_type_code
PICKING_TYPE_LABEL = {
    "outgoing": "Delivery Order",
    "incoming": "Receipt",
    "internal": "Internal Transfer",
}

# Map state+type to the correct report
# - assigned (ready)  → picking operations sheet  → stock.report_picking
# - done              → delivery slip / receipt   → stock.report_deliveryslip
PICKING_STATE_REPORT = {
    "assigned": "stock.report_picking",
    "done":     "stock.report_deliveryslip",
}


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def action_custom_print_dialog(self):
        """
        Opens the custom print preview dialog for a stock picking.

        Replaces two original buttons:
          - do_print_picking (object)  → state == 'assigned'
            uses: stock.report_picking   (Picking Operations sheet)
          - 356 (action)               → state == 'done'
            uses: stock.report_deliveryslip  (Delivery Slip / Receipt)
        """
        self.ensure_one()

        report_name = PICKING_STATE_REPORT.get(self.state, "stock.report_deliveryslip")
        doc_label   = PICKING_TYPE_LABEL.get(
            self.picking_type_code,
            "Transfer"
        )
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