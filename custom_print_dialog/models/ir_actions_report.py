# -*- coding: utf-8 -*-
from odoo import models, api


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    @api.model
    def get_xml_export(self, report_name, record_ids):
        """
        Called via JSON-RPC from the print dialog JS to generate XML content.
        Returns XML as a string — avoids any HTTP controller routing issues.
        """
        report_action = self.search([("report_name", "=", report_name)], limit=1)

        # Try native qweb-xml renderer (e.g. e-invoicing reports)
        if report_action and report_action.report_type == "qweb-xml":
            xml_bytes, _ctype = report_action._render_qweb_xml(report_name, record_ids)
            return xml_bytes.decode("utf-8")

        # Fallback: export record fields as structured XML
        model_name = report_action.model if report_action else None
        if not model_name:
            return '<?xml version="1.0"?><error>XML export not available for this report</error>'

        records = self.env[model_name].browse(record_ids)
        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<records>"]

        for record in records:
            xml_lines.append(f'  <record model="{model_name}" id="{record.id}">')
            for field_name, field in record._fields.items():
                if field.type in ("many2many", "one2many", "binary"):
                    continue
                try:
                    val = record[field_name]
                    if hasattr(val, "name"):
                        val = val.name or ""
                    elif hasattr(val, "id"):
                        val = str(val.id)
                    else:
                        val = str(val) if val is not False and val is not None else ""
                    safe = (str(val)
                            .replace("&", "&amp;")
                            .replace("<", "&lt;")
                            .replace(">", "&gt;")
                            .replace('"', "&quot;"))
                    xml_lines.append(f'    <field name="{field_name}">{safe}</field>')
                except Exception:
                    pass
            xml_lines.append("  </record>")

        xml_lines.append("</records>")
        return "\n".join(xml_lines)