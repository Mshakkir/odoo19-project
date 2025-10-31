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
                # Join with analytic distribution table
                tables += " LEFT JOIN account_analytic_line aal ON account_move_line.id = aal.move_line_id"
                wheres.append("aal.account_id IN %s")
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

    def get_account_lines(self, data):
        """Override to handle separate reports per analytic account"""
        analytic_account_ids = data.get('analytic_account_ids', [])
        analytic_filter_mode = data.get('analytic_filter_mode', 'combined')

        # If no analytic accounts selected or combined mode, use original logic
        if not analytic_account_ids or analytic_filter_mode == 'combined':
            return super(ReportFinancialInherit, self).get_account_lines(data)

        # Separate mode: generate lines for each analytic account
        all_lines = []
        for analytic_id in analytic_account_ids:
            analytic_account = self.env['account.analytic.account'].browse(analytic_id)

            # Add section header for this analytic account
            all_lines.append({
                'name': f'=== {analytic_account.name} ===',
                'balance': 0.0,
                'type': 'report',
                'level': 1,
                'account_type': False,
            })

            # Get lines for this specific analytic account
            temp_data = data.copy()
            temp_data['used_context'] = dict(data.get('used_context', {}))
            temp_data['used_context']['analytic_account_ids'] = [analytic_id]

            lines = super(ReportFinancialInherit, self).get_account_lines(temp_data)
            all_lines.extend(lines)

            # Add spacing
            all_lines.append({
                'name': '',
                'balance': 0.0,
                'type': 'report',
                'level': 0,
                'account_type': False,
            })

        return all_lines

    @api.model
    def _get_report_values(self, docids, data=None):
        """Override to pass analytic account info to template"""
        result = super(ReportFinancialInherit, self)._get_report_values(docids, data)

        # Add analytic account information to the report
        if data and data.get('form'):
            analytic_account_ids = data['form'].get('analytic_account_ids', [])
            if analytic_account_ids:
                analytic_accounts = self.env['account.analytic.account'].browse(analytic_account_ids)
                result['analytic_accounts'] = analytic_accounts
                result['analytic_filter_mode'] = data['form'].get('analytic_filter_mode', 'combined')

        return result