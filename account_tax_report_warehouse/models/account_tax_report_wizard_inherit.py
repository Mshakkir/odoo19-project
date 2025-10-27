from odoo import api, fields, models


class AccountTaxReportWizard(models.TransientModel):
    _inherit = "account.tax.report.wizard"

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string="Analytic Accounts (Warehouses)",
        help="Filter Tax Report based on selected warehouse analytic accounts."
    )

    def _print_report(self):
        """Override the print logic to include analytic filter."""
        form_data = self.read(['date_from', 'date_to', 'target_move', 'analytic_account_ids'])[0]

        analytic_ids = form_data.get('analytic_account_ids', [])
        if analytic_ids and isinstance(analytic_ids[0], (tuple, list)):
            analytic_ids = analytic_ids[0][2]
        form_data['analytic_account_ids'] = analytic_ids

        # Prepare report action
        action = self.env.ref('accounting_pdf_reports.action_report_account_tax').report_action(
            self,
            data={'form': form_data}
        )
        return action


class AccountTaxReportCustom(models.AbstractModel):
    _inherit = "report.accounting_pdf_reports.account_tax_report"

    @api.model
    def _get_report_values(self, docids, data=None):
        """Inject analytic filter into the move line domain."""
        res = super()._get_report_values(docids, data=data)
        form = data.get('form', {})

        analytic_ids = form.get('analytic_account_ids', [])
        if analytic_ids:
            # Make sure we have IDs as integers
            analytic_ids = [int(x) for x in analytic_ids]

            # Recompute lines based on analytic filter
            move_line_obj = self.env['account.move.line']

            domain = [
                ('tax_line_id', '!=', False),
                ('parent_state', '=', 'posted'),
                ('move_id.move_type', 'in', ['out_invoice', 'in_invoice', 'out_refund', 'in_refund']),
            ]

            # Add date range filter
            if form.get('date_from'):
                domain.append(('date', '>=', form['date_from']))
            if form.get('date_to'):
                domain.append(('date', '<=', form['date_to']))

            # Add analytic filter (works with both analytic_line_ids and analytic_distribution)
            domain.append('|')
            domain.append(('analytic_line_ids.account_id', 'in', analytic_ids))
            domain.append(('analytic_distribution', '!=', False))

            move_lines = move_line_obj.search(domain)

            # Group by tax
            tax_summary = {}
            for line in move_lines:
                tax = line.tax_line_id
                if not tax:
                    continue
                if tax.id not in tax_summary:
                    tax_summary[tax.id] = {
                        'tax': tax,
                        'base': 0.0,
                        'amount': 0.0,
                    }
                tax_summary[tax.id]['base'] += abs(line.tax_base_amount)
                tax_summary[tax.id]['amount'] += abs(line.balance)

            res['Taxes'] = list(tax_summary.values())
            res['analytic_account_ids'] = analytic_ids

        return res
