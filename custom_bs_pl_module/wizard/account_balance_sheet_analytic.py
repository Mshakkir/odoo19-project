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

    def _get_filters(self):
        """Extend filter values to include analytic accounts."""
        res = super()._get_filters()
        res['warehouse_analytic_ids'] = self.warehouse_analytic_ids.ids
        return res

    def _print_report(self, data):
        """Override report printing to include analytic filters."""
        data = self._get_filters()
        data.update({
            'form': self.read([
                'date_from',
                'date_to',
                'warehouse_analytic_ids',
            ])[0]
        })
        # ✅ Use existing Odoo Mates Balance Sheet action
        return self.env.ref('accounting_pdf_reports.action_report_financial') \
            .with_context(landscape=True) \
            .report_action(self, data=data)
