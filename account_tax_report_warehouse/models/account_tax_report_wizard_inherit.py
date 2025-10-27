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


class AccountTaxReport(models.AbstractModel):
    _inherit = 'report.accounting_pdf_reports.report_tax'

    def _line_has_analytic_account(self, line, analytic_ids):
        """Check if move line has any of the specified analytic accounts."""
        if not line.analytic_distribution:
            return False

        # analytic_distribution is a JSON field: {"account_id": percentage}
        # Example: {"1": 100.0, "2": 50.0}
        try:
            for account_id_str in line.analytic_distribution.keys():
                if int(account_id_str) in analytic_ids:
                    return True
        except (ValueError, AttributeError, TypeError):
            # Handle any parsing issues
            return False
        return False

    def _get_line_analytic_amount(self, line, analytic_ids):
        """Get the proportional amount of a line based on analytic distribution."""
        if not line.analytic_distribution:
            return 0.0

        # Calculate the percentage allocated to the selected analytic accounts
        percentage = 0.0
        try:
            for account_id_str, dist_percentage in line.analytic_distribution.items():
                if int(account_id_str) in analytic_ids:
                    percentage += float(dist_percentage)
        except (ValueError, AttributeError, TypeError):
            return 0.0

        # Return proportional amount
        return line.balance * (percentage / 100.0)

    @api.model
    def _get_report_values(self, docids, data=None):
        """Override the report model's _get_report_values to filter by analytic accounts."""
        # Always call parent first to get the correct structure
        res = super()._get_report_values(docids, data=data)

        if not data or not data.get('form'):
            return res

        form = data['form']
        analytic_ids = form.get('analytic_account_ids', [])

        # If NO analytic filter is applied, use parent method result as-is
        if not analytic_ids:
            return res

        # DEBUG: Log what we're filtering by
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info(f"=== ANALYTIC FILTER ACTIVE ===")
        _logger.info(f"Selected Analytic Account IDs: {analytic_ids}")

        # If analytic filter IS applied, recalculate only the taxes
        date_from = form.get('date_from')
        date_to = form.get('date_to')
        target_move = form.get('target_move', 'posted')

        # Build base domain for filtering
        domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]

        if target_move == 'posted':
            domain.append(('move_id.state', '=', 'posted'))

        # Get all taxes
        taxes = self.env['account.tax'].search([])
        tax_data = []

        for tax in taxes:
            # Get tax lines
            tax_domain = domain + [('tax_line_id', '=', tax.id)]
            all_tax_lines = self.env['account.move.line'].search(tax_domain)

            # Filter by analytic distribution and calculate proportional amounts
            filtered_tax_lines = all_tax_lines.filtered(
                lambda l: self._line_has_analytic_account(l, analytic_ids)
            )

            # Calculate tax amount based on analytic distribution percentages
            tax_amount = sum(self._get_line_analytic_amount(line, analytic_ids) for line in filtered_tax_lines)

            # Get base lines (lines where this tax was applied)
            base_domain = domain + [('tax_ids', 'in', [tax.id])]
            all_base_lines = self.env['account.move.line'].search(base_domain)

            # Filter by analytic distribution and calculate proportional amounts
            filtered_base_lines = all_base_lines.filtered(
                lambda l: self._line_has_analytic_account(l, analytic_ids)
            )
            # Calculate base amount based on analytic distribution percentages
            base_amount = sum(self._get_line_analytic_amount(line, analytic_ids) for line in filtered_base_lines)

            # Only include if has amounts
            if base_amount or tax_amount:
                tax_data.append({
                    'id': tax.id,
                    'name': tax.name,
                    'base_amount': base_amount,
                    'tax_amount': tax_amount,
                    'type_tax_use': tax.type_tax_use,
                })

        _logger.info(f"Total taxes in filtered report: {len(tax_data)}")
        _logger.info(f"=== END ANALYTIC FILTER ===")

        # Only override the taxes, keep everything else from parent
        res['taxes'] = tax_data

        return res