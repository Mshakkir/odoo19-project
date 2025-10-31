from odoo import api, models


class ReportFinancialInherit(models.AbstractModel):
    _inherit = 'report.accounting_pdf_reports.report_financial'

    def _compute_account_balance(self, accounts):
        """Override to add analytic account filtering"""
        mapping = {
            'balance': "COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance",
            'debit': "COALESCE(SUM(debit), 0) as debit",
            'credit': "COALESCE(SUM(credit), 0) as credit",
        }

        res = {}
        for account in accounts:
            res[account.id] = dict.fromkeys(mapping, 0.0)

        if accounts:
            tables, where_clause, where_params = self.env['account.move.line']._query_get()
            tables = tables.replace('"', '') if tables else "account_move_line"
            wheres = [""]

            if where_clause.strip():
                wheres.append(where_clause.strip())

            # Add analytic account filter from context
            analytic_account_ids = self.env.context.get('analytic_account_ids', [])
            if analytic_account_ids:
                # Check if analytic lines exist, filter by them
                wheres.append("""
                    EXISTS (
                        SELECT 1 FROM account_analytic_line aal 
                        WHERE aal.move_line_id = account_move_line.id 
                        AND aal.account_id IN %s
                    )
                """)
                where_params = list(where_params) + [tuple(analytic_account_ids)]
                where_params = tuple(where_params)

            filters = " AND ".join(wheres)
            request = "SELECT account_id as id, " + ', '.join(mapping.values()) + \
                      " FROM " + tables + \
                      " WHERE account_id IN %s " \
                      + filters + \
                      " GROUP BY account_id"
            params = (tuple(accounts._ids),) + tuple(where_params)
            self.env.cr.execute(request, params)
            for row in self.env.cr.dictfetchall():
                res[row['id']] = row

        return res

    @api.model
    def _get_report_values(self, docids, data=None):
        """Override to handle separate reports per analytic account"""
        if not data or not data.get('form'):
            return super(ReportFinancialInherit, self)._get_report_values(docids, data)

        analytic_account_ids = data['form'].get('analytic_account_ids', [])
        analytic_filter_mode = data['form'].get('analytic_filter_mode', 'combined')

        # If separate mode and analytic accounts selected, generate multiple reports
        if analytic_account_ids and analytic_filter_mode == 'separate':
            all_reports = []

            for analytic_id in analytic_account_ids:
                analytic_account = self.env['account.analytic.account'].browse(analytic_id)

                # Create a copy of data with single analytic account
                single_data = data.copy()
                single_data['form'] = data['form'].copy()
                single_data['form']['used_context'] = dict(data['form'].get('used_context', {}))
                single_data['form']['used_context']['analytic_account_ids'] = [analytic_id]

                # Get report lines for this analytic account
                report_lines = self.get_account_lines(single_data['form'])

                all_reports.append({
                    'analytic_account': analytic_account,
                    'report_lines': report_lines,
                    'data': single_data['form'],
                })

            # Return data for separate template
            model = self.env.context.get('active_model')
            docs = self.env[model].browse(self.env.context.get('active_id'))

            return {
                'doc_ids': self.ids,
                'doc_model': model,
                'data': data['form'],
                'docs': docs,
                'time': __import__('time'),
                'all_reports': all_reports,
                'analytic_filter_mode': 'separate',
            }

        # Combined mode or no analytic accounts - use original logic
        result = super(ReportFinancialInherit, self)._get_report_values(docids, data)

        # Add analytic info for display in combined mode
        if analytic_account_ids:
            analytic_accounts = self.env['account.analytic.account'].browse(analytic_account_ids)
            result['analytic_accounts'] = analytic_accounts
            result['analytic_filter_mode'] = 'combined'

        return result

