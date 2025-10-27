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

    def _print_report(self):
        """Override to pass analytic filter to report."""
        form_data = self.read(['date_from', 'date_to', 'target_move', 'analytic_account_ids'])[0]

        # Normalize analytic_account_ids
        analytic_ids = form_data.get('analytic_account_ids', [])
        if analytic_ids and isinstance(analytic_ids[0], (tuple, list)):
            analytic_ids = analytic_ids[0][2]  # get IDs from [(6, 0, [ids])]
        form_data['analytic_account_ids'] = analytic_ids

        return self.env.ref('accounting_pdf_reports.action_report_account_tax').report_action(
            self, data={'form': form_data}
        )

    @api.model
    def _get_report_values(self, docids, data=None):
        """Override to inject analytic filter and filter the actual data."""
        res = super()._get_report_values(docids, data=data)

        if not data or not data.get('form'):
            return res

        form = data.get('form', {})
        analytic_ids = form.get('analytic_account_ids', [])

        if analytic_ids:
            # Filter the taxes data based on analytic accounts
            filtered_taxes = []

            # Get the taxes from the result
            taxes_data = res.get('taxes', [])

            for tax in taxes_data:
                # Get move lines related to this tax filtered by analytic
                filtered_base_amount = 0.0
                filtered_tax_amount = 0.0

                # Query move lines with analytic filter
                domain = [
                    ('date', '>=', form.get('date_from')),
                    ('date', '<=', form.get('date_to')),
                    ('tax_line_id', '=', tax.get('id')),
                    ('analytic_account_id', 'in', analytic_ids),
                ]

                if form.get('target_move') == 'posted':
                    domain.append(('move_id.state', '=', 'posted'))

                # Get tax lines
                tax_lines = self.env['account.move.line'].search(domain)
                filtered_tax_amount = sum(tax_lines.mapped('balance'))

                # Get base lines (lines where this tax was applied)
                base_domain = [
                    ('date', '>=', form.get('date_from')),
                    ('date', '<=', form.get('date_to')),
                    ('tax_ids', 'in', [tax.get('id')]),
                    ('analytic_account_id', 'in', analytic_ids),
                ]

                if form.get('target_move') == 'posted':
                    base_domain.append(('move_id.state', '=', 'posted'))

                base_lines = self.env['account.move.line'].search(base_domain)
                filtered_base_amount = sum(base_lines.mapped('balance'))

                # Only include tax if it has amounts
                if filtered_base_amount or filtered_tax_amount:
                    tax_copy = tax.copy()
                    tax_copy['base_amount'] = filtered_base_amount
                    tax_copy['tax_amount'] = filtered_tax_amount
                    filtered_taxes.append(tax_copy)

            res['taxes'] = filtered_taxes
            res['data']['form']['analytic_account_ids'] = analytic_ids

        return res


class AccountTaxReport(models.AbstractModel):
    _inherit = 'report.accounting_pdf_reports.report_tax'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Override the report model's _get_report_values."""
        if not data or not data.get('form'):
            return super()._get_report_values(docids, data=data)

        form = data['form']
        analytic_ids = form.get('analytic_account_ids', [])
        date_from = form.get('date_from')
        date_to = form.get('date_to')
        target_move = form.get('target_move', 'posted')

        # Build domain for filtering
        domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]

        if target_move == 'posted':
            domain.append(('move_id.state', '=', 'posted'))

        # If analytic filter is applied
        if analytic_ids:
            domain.append(('analytic_account_id', 'in', analytic_ids))

            # Get all taxes
            taxes = self.env['account.tax'].search([])
            tax_data = []

            for tax in taxes:
                # Get tax lines
                tax_domain = domain + [('tax_line_id', '=', tax.id)]
                tax_lines = self.env['account.move.line'].search(tax_domain)
                tax_amount = sum(tax_lines.mapped('balance'))

                # Get base lines
                base_domain = domain + [('tax_ids', 'in', [tax.id])]
                base_lines = self.env['account.move.line'].search(base_domain)
                base_amount = sum(base_lines.mapped('balance'))

                # Only include if has amounts
                if base_amount or tax_amount:
                    tax_data.append({
                        'id': tax.id,
                        'name': tax.name,
                        'base_amount': base_amount,
                        'tax_amount': tax_amount,
                        'type_tax_use': tax.type_tax_use,
                    })

            return {
                'doc_ids': docids,
                'doc_model': 'account.tax.report.wizard',
                'data': data,
                'docs': self.env['account.tax.report.wizard'].browse(docids),
                'taxes': tax_data,
                'date_from': date_from,
                'date_to': date_to,
            }

        # No analytic filter - use parent method
        return super()._get_report_values(docids, data=data)
