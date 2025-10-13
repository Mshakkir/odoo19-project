# Copyright 2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class VATReportWizard(models.TransientModel):
    _name = "vat.report.wizard"
    _description = "VAT Report Wizard"

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    date_range_id = fields.Many2one(
        comodel_name="date.range",
        string="Date range"
    )
    date_from = fields.Date("Start Date", required=True)
    date_to = fields.Date("End Date", required=True)
    based_on = fields.Selection(
        [("taxtags", "Tax Tags"), ("taxgroups", "Tax Groups")],
        required=True,
        default="taxtags",
    )
    tax_detail = fields.Boolean("Detail Taxes")
    target_move = fields.Selection(
        [("posted", "All Posted Entries"), ("all", "All Entries")],
        string="Target Moves",
        required=True,
        default="posted",
    )

    @api.onchange("company_id")
    def onchange_company_id(self):
        if (
                self.company_id
                and self.date_range_id.company_id
                and self.date_range_id.company_id != self.company_id
        ):
            self.date_range_id = False
        res = {"domain": {"date_range_id": []}}
        if not self.company_id:
            return res
        else:
            res["domain"]["date_range_id"] += [
                "|",
                ("company_id", "=", self.company_id.id),
                ("company_id", "=", False),
            ]
        return res

    @api.onchange("date_range_id")
    def onchange_date_range_id(self):
        """Handle date range change."""
        if self.date_range_id:
            self.date_from = self.date_range_id.date_start
            self.date_to = self.date_range_id.date_end

    @api.constrains("company_id", "date_range_id")
    def _check_company_id_date_range_id(self):
        for rec in self.sudo():
            if (
                    rec.company_id
                    and rec.date_range_id.company_id
                    and rec.company_id != rec.date_range_id.company_id
            ):
                raise ValidationError(
                    "The Company in the VAT Report Wizard and in "
                    "Date Range must be the same."
                )

    def _print_report(self, report_type):
        self.ensure_one()
        data = self._prepare_vat_report()
        if report_type == "xlsx":
            # For XLSX, you'll need to install report_xlsx module
            report_name = "vat_report.report_vat_report_xlsx"
        else:
            report_name = "vat_report.vat_report_pdf"

        return self.env.ref(report_name).report_action(self, data=data)

    def _prepare_vat_report(self):
        self.ensure_one()
        return {
            "wizard_id": self.id,
            "company_id": self.company_id.id,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "based_on": self.based_on,
            "only_posted_moves": self.target_move == "posted",
            "tax_detail": self.tax_detail,
        }

    def button_export_html(self):
        """View report in HTML format."""
        self.ensure_one()
        action = {
            'type': 'ir.actions.client',
            'name': 'VAT Report',
            'tag': 'vat_report',
            'context': {
                'wizard_id': self.id,
                'company_id': self.company_id.id,
                'date_from': str(self.date_from),
                'date_to': str(self.date_to),
                'based_on': self.based_on,
                'only_posted_moves': self.target_move == "posted",
                'tax_detail': self.tax_detail,
            }
        }
        return action

    def button_export_pdf(self):
        """Export report as PDF."""
        return self._print_report("pdf")

    def button_export_xlsx(self):
        """Export report as XLSX."""
        return self._print_report("xlsx")