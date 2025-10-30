# -*- coding: utf-8 -*-
from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class AccountingReportAnalytic(models.TransientModel):
    _inherit = 'accounting.report'

    warehouse_analytic_ids = fields.Many2many(
        'account.analytic.account',
        string='Warehouse Analytic Accounts',
        help="Filter Balance Sheet / P&L by analytic accounts (warehouses)."
    )

    def _get_filter_values(self):
        """Build a dictionary in the format expected by accounting_pdf_reports."""
        form_data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'target_move': self.target_move,
            'warehouse_analytic_ids': self.warehouse_analytic_ids.ids,
            'company_id': self.company_id.id if self.company_id else False,
        }
        return {'form': form_data}

    def _print_report(self, data):
        """Override report printing to include analytic filters."""
        data = self._get_filter_values()
        _logger.info("Printing report with filters: %s", data)

        # Use the existing Odoo Mates balance sheet action
        return self.env.ref(
            'accounting_pdf_reports.action_report_financial'
        ).with_context(landscape=True).report_action(self, data=data)
