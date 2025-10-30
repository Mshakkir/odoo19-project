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

    def get_filters(self, default_filters=None):
        """Extend filter values to include analytic accounts."""
        res = super(AccountingReportAnalytic, self).get_filters(default_filters)
        res['warehouse_analytic_ids'] = self.warehouse_analytic_ids.ids
        return res

    def _print_report(self, data):
        """Override report printing to include analytic filters."""
        data = self.get_filters()

        _logger.info("Printing financial report with analytic filters: %s", data)

        return self.env.ref(
            'accounting_pdf_reports.action_report_financial'
        ).with_context(landscape=True).report_action(self, data=data)
