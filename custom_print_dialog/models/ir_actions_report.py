# -*- coding: utf-8 -*-
from odoo import models, api


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    @api.model
    def get_excel_export_data(self, report_name, record_ids):
        """
        Called via ORM RPC from the print dialog to get structured data for Excel.
        Returns a dict with headers and rows that SheetJS uses to build the .xlsx.
        Works for any report model — extracts field values from the record.
        """
        report_action = self.search([("report_name", "=", report_name)], limit=1)
        if not report_action:
            return {"headers": ["Error"], "rows": [["Report not found"]], "sheet_name": "Report"}

        model_name = report_action.model
        records    = self.env[model_name].browse(record_ids)

        # Build column list — skip binary/relational fields and internal fields
        SKIP_TYPES   = {"many2many", "one2many", "binary", "html", "serialized"}
        SKIP_PREFIXES = ("message_", "activity_", "website_", "access_")

        fields_meta = [
            (fname, field)
            for fname, field in records._fields.items()
            if field.type not in SKIP_TYPES
            and not fname.startswith(SKIP_PREFIXES)
            and not fname.startswith("_")
        ]

        headers = [field.string or fname for fname, field in fields_meta]
        rows    = []

        for record in records:
            row = []
            for fname, field in fields_meta:
                try:
                    val = record[fname]
                    if val is False or val is None:
                        val = ""
                    elif field.type in ("many2one",):
                        val = val.display_name if val else ""
                    elif field.type == "date":
                        val = str(val) if val else ""
                    elif field.type == "datetime":
                        val = str(val) if val else ""
                    elif field.type == "boolean":
                        val = "Yes" if val else "No"
                    elif field.type in ("float", "monetary", "integer"):
                        val = val  # keep numeric for Excel
                    else:
                        val = str(val)
                except Exception:
                    val = ""
                row.append(val)
            rows.append(row)

        # Use the record name or model as sheet name (max 31 chars for Excel)
        sheet_name = (report_action.name or model_name)[:31]

        return {
            "headers":    headers,
            "rows":       rows,
            "sheet_name": sheet_name,
        }