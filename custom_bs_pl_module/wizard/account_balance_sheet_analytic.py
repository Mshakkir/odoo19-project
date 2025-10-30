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
        """Extend filter values to include analytic accounts."""
        # call the existing filter method in Odoo Mates' accounting.report
        res = super()._get_filter_values()
        res['warehouse_analytic_ids'] = self.warehouse_analytic_ids.ids
        return res

    def _print_report(self, data):
        """Override report printing to include analytic filters."""
        data = self._get_filter_values()

        _logger.info("Printing financial report with analytic filters: %s", data)

        # use Odoo Mates' report action reference
        return self.env.ref(
            'accounting_pdf_reports.action_report_financial'
        ).with_context(landscape=True).report_action(self, data=data)
