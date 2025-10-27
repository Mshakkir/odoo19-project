# from odoo import api, fields, models
#
# class AccountTaxReportWizard(models.TransientModel):
#     _inherit = "account.tax.report.wizard"
#
#     analytic_account_ids = fields.Many2many(
#         'account.analytic.account',
#         string="Analytic Accounts (Warehouses)",
#         help="Filter Tax Report based on selected warehouse analytic accounts."
#     )
#
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         """Inject analytic filter into report context."""
#         res = super()._get_report_values(docids, data=data)
#         if data and data.get('form') and data['form'].get('analytic_account_ids'):
#             analytic_ids = data['form']['analytic_account_ids']
#             res['data']['form']['analytic_account_ids'] = analytic_ids
#         return res
# def _print_report(self):
#     form_data = self.read(['date_from', 'date_to', 'target_move', 'analytic_account_ids'])[0]
#
#     # Normalize analytic_account_ids
#     analytic_ids = form_data.get('analytic_account_ids', [])
#     if analytic_ids and isinstance(analytic_ids[0], (tuple, list)):
#         analytic_ids = analytic_ids[0][2]  # get IDs from [(6, 0, [ids])]
#     form_data['analytic_account_ids'] = analytic_ids
#
#     return self.env.ref('accounting_pdf_reports.action_report_account_tax').report_action(self, data={'form': form_data})
#
from odoo import api, fields, models


class AccountTaxReportWizard(models.TransientModel):
    _inherit = "account.tax.report.wizard"

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string="Analytic Accounts (Warehouses)",
        help="Filter Tax Report based on selected warehouse analytic accounts."
    )

    def _print_report(self, data=None):
        """Override to pass analytic filter to report."""
        if data is None:
            data = {}

        form_data = self.read(['date_from', 'date_to', 'target_move', 'analytic_account_ids'])[0]

        # Normalize analytic_account_ids
        analytic_ids = form_data.get('analytic_account_ids', [])
        if analytic_ids and isinstance(analytic_ids[0], (tuple, list)):
            analytic_ids = analytic_ids[0][2]  # get IDs from [(6, 0, [ids])]
        form_data['analytic_account_ids'] = analytic_ids

        # Merge with existing data
        data.update({'form': form_data})

        return self.env.ref('accounting_pdf_reports.action_report_account_tax').report_action(
            self, data=data
        )


class ReportTax(models.AbstractModel):
    _inherit = 'report.accounting_pdf_reports.report_tax'

    def _compute_from_amls(self, options, taxes):
        """Override to add analytic account filtering."""
        import logging
        _logger = logging.getLogger(__name__)

        analytic_ids = options.get('analytic_account_ids', [])

        if not analytic_ids:
            # No filter - use parent method
            return super()._compute_from_amls(options, taxes)

        _logger.info(f"=== ANALYTIC FILTER IN _compute_from_amls ===")
        _logger.info(f"Filtering by analytic accounts: {analytic_ids}")

        # Compute tax amounts with analytic filter
        sql = self._sql_from_amls_one()
        tables, where_clause, where_params = self.env['account.move.line']._query_get()

        # Add analytic distribution filter
        # In Odoo 19, analytic_distribution is JSON: {"account_id": percentage}
        # We need to check if any of our analytic_ids exist in the JSON keys
        analytic_filter = " AND ("
        analytic_conditions = []
        for analytic_id in analytic_ids:
            analytic_conditions.append(f"account_move_line.analytic_distribution ? '{analytic_id}'")
        analytic_filter += " OR ".join(analytic_conditions)
        analytic_filter += ")"

        where_clause += analytic_filter

        # Execute query for tax amounts
        query = sql % (tables, where_clause)
        _logger.info(f"Tax amount query: {query}")
        _logger.info(f"Query params: {where_params}")

        self.env.cr.execute(query, where_params)
        results = self.env.cr.fetchall()

        _logger.info(f"Tax amount results count: {len(results)}")

        for result in results:
            if result[0] in taxes:
                taxes[result[0]]['tax'] = abs(result[1])
                _logger.info(f"  Tax ID {result[0]}: tax amount = {abs(result[1])}")

        # Compute net amounts (base) with analytic filter
        sql2 = self._sql_from_amls_two()
        query = sql2 % (tables, where_clause)

        self.env.cr.execute(query, where_params)
        results = self.env.cr.fetchall()

        _logger.info(f"Base amount results count: {len(results)}")

        for result in results:
            if result[0] in taxes:
                taxes[result[0]]['net'] = abs(result[1])
                _logger.info(f"  Tax ID {result[0]}: base amount = {abs(result[1])}")

        _logger.info(f"=== END ANALYTIC FILTER ===")