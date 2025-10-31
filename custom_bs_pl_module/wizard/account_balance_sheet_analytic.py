# -*- coding: utf-8 -*-
from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class AccountingReportAnalytic(models.TransientModel):
    _inherit = 'accounting.report'  # ✅ Fixed: was 'account.balance.report'

    warehouse_analytic_ids = fields.Many2many(
        'account.analytic.account',
        string='Warehouse Analytic Accounts',
        help="Filter the Balance Sheet and Profit & Loss reports by specific warehouse analytic accounts."
    )

    def _print_report(self, data):
        """
        Override the print report to pass analytic filters to Odoo Mates' accounting_pdf_reports.
        """
        # Build the data dictionary expected by accounting_pdf_reports
        form_data = self.read()[0]

        # Add our analytic filters manually
        form_data.update({
            'warehouse_analytic_ids': self.warehouse_analytic_ids.ids,
        })

        data = {'form': form_data}

        _logger.info("✅ Final report data sent to Odoo Mates: %s", data)

        # Call the Odoo Mates report action
        return self.env.ref(
            'accounting_pdf_reports.action_report_financial'
        ).report_action(self, data=data)