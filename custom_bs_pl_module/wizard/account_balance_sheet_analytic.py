# -*- coding: utf-8 -*-
from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)

class AccountingReportAnalytic(models.TransientModel):
    _inherit = 'accounting.report'

    warehouse_analytic_ids = fields.Many2many(
        'account.analytic.account',
        string='Warehouse Analytic Accounts',
        help="Filter balance sheet by analytic accounts (warehouses)."
    )

    def _get_filter_values(self):
        """Extend filter values to include analytic accounts."""
        res = super()._get_filter_values()
        res['warehouse_analytic_ids'] = self.warehouse_analytic_ids.ids
        return res

    def _build_contexts(self, data):
        """Extend the default context with warehouse analytic filters."""
        result = super()._build_contexts(data)
        result['warehouse_analytic_ids'] = data.get('warehouse_analytic_ids', [])
        return result

    def _print_report(self, data):
        """
        Properly pass data to Odoo Mates accounting_pdf_reports action.
        """
        # Create base data dict in the same structure as Odoo Mates
        data = {
            'form': self.read()[0]
        }

        # Include your analytic filter
        data['form'].update(self._get_filter_values())

        _logger.info("✅ Sending data to Odoo Mates financial report: %s", data)

        # Trigger Odoo Mates’ Balance Sheet / Profit & Loss report action
        return self.env.ref('accounting_pdf_reports.action_report_financial').report_action(self, data=data)
