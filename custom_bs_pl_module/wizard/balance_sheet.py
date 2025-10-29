# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountingReport(models.TransientModel):
    _inherit = 'accounting.report'

    # -------------------------------
    # NEW FIELD: Warehouse Analytic
    # -------------------------------
    warehouse_analytic_id = fields.Many2one(
        'account.analytic.account',
        string='Warehouse (Analytic)',
        help='Select warehouse analytic account to filter the report.'
    )

    @api.onchange('warehouse_analytic_id')
    def _onchange_warehouse_analytic_id(self):
        """When warehouse is selected, set default report if needed."""
        if self.warehouse_analytic_id:
            self.account_report_id = self.env.ref(
                'accounting_pdf_reports.account_financial_report_balancesheet0'
            ).id

    # ---------------------------------------------------------
    # ADD YOUR FILTER LOGIC HERE (Step 3)
    # ---------------------------------------------------------
    def action_view_balance_sheet_details(self):
        """Generate balance sheet lines, filtered by analytic account if chosen."""
        self.ensure_one()

        # Start building domain for report lines
        domain = []

        # ✅ If warehouse analytic account selected, filter by it
        if self.warehouse_analytic_id:
            domain.append(('analytic_account_id', '=', self.warehouse_analytic_id.id))

        # Example: Fetch account move lines
        move_lines = self.env['account.move.line'].search(domain)

        # Example: You can print/log it for debugging
        # print("Filtered Move Lines:", move_lines.mapped('name'))

        # Continue your balance sheet generation logic here...
        # (If your base code already defines this method in super, call it)
        res = super(AccountingReport, self).action_view_balance_sheet_details()

        return res
