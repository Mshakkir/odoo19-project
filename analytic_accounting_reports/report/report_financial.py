from odoo import api, models


class ReportFinancial(models.AbstractModel):
    _inherit = 'report.accounting_pdf_reports.report_financial'

    def _compute_account_balance(self, accounts):
        """Override to add analytic distribution filtering"""
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

            # Add analytic distribution filtering
            analytic_account_id = self.env.context.get('analytic_account_id')
            if analytic_account_id:
                # Filter by analytic distribution JSON field
                wheres.append(f"analytic_distribution ? '{analytic_account_id}'")

            filters = " AND ".join(wheres)
            request = "SELECT account_id as id, " + ', '.join(mapping.values()) + \
                      " FROM " + tables + \
                      " WHERE account_id IN %s " + filters + \
                      " GROUP BY account_id"
            params = (tuple(accounts._ids),) + tuple(where_params)
            self.env.cr.execute(request, params)
            for row in self.env.cr.dictfetchall():
                res[row['id']] = row

        return res

    def _get_analytic_breakdown(self, accounts):
        """Get balance breakdown by analytic accounts for given accounts"""
        if not accounts:
            return {}

        # Get all analytic accounts (warehouses)
        analytic_accounts = self.env['account.analytic.account'].search([
            ('plan_id.name', 'ilike', 'warehouse')  # Adjust based on your plan naming
        ])

        result = {}
        for account in accounts:
            result[account.id] = {}
            for analytic in analytic_accounts:
                result[account.id][analytic.id] = {'balance': 0.0, 'debit': 0.0, 'credit': 0.0}

        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = tables.replace('"', '') if tables else "account_move_line"

        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())

        for analytic in analytic_accounts:
            # Query for each analytic account
            analytic_where = wheres + [f"analytic_distribution ? '{analytic.id}'"]
            filters = " AND ".join(analytic_where)

            request = """
                SELECT account_id, 
                       COALESCE(SUM(debit), 0) as debit,
                       COALESCE(SUM(credit), 0) as credit,
                       COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0) as balance
                FROM """ + tables + """
                WHERE account_id IN %s """ + filters + """
                GROUP BY account_id
            """
            params = (tuple(accounts._ids),) + tuple(where_params)
            self.env.cr.execute(request, params)

            for row in self.env.cr.dictfetchall():
                if row['account_id'] in result:
                    result[row['account_id']][analytic.id] = {
                        'balance': row['balance'],
                        'debit': row['debit'],
                        'credit': row['credit']
                    }

        return result, analytic_accounts

    def get_account_lines(self, data):
        """Override to add analytic breakdown if requested"""
        lines = []
        account_report = self.env['account.financial.report'].search(
            [('id', '=', data['account_report_id'][0])])
        child_reports = account_report._get_children_by_order()

        # Set context for analytic filtering
        context = data.get('used_context', {})
        res = self.with_context(context)._compute_report_balance(child_reports)

        # Handle comparison
        if data['enable_filter']:
            comparison_res = self.with_context(
                data.get('comparison_context'))._compute_report_balance(child_reports)
            for report_id, value in comparison_res.items():
                res[report_id]['comp_bal'] = value['balance']
                report_acc = res[report_id].get('account')
                if report_acc:
                    for account_id, val in comparison_res[report_id].get('account').items():
                        report_acc[account_id]['comp_bal'] = val['balance']

        # Build report lines
        for report in child_reports:
            vals = {
                'name': report.name,
                'balance': res[report.id]['balance'] * float(report.sign),
                'type': 'report',
                'level': bool(report.style_overwrite) and report.style_overwrite or report.level,
                'account_type': report.type or False,
            }

            if data['debit_credit']:
                vals['debit'] = res[report.id]['debit']
                vals['credit'] = res[report.id]['credit']

            if data['enable_filter']:
                vals['balance_cmp'] = res[report.id]['comp_bal'] * float(report.sign)

            lines.append(vals)

            if report.display_detail == 'no_detail':
                continue

            if res[report.id].get('account'):
                sub_lines = []
                for account_id, value in res[report.id]['account'].items():
                    flag = False
                    account = self.env['account.account'].browse(account_id)
                    vals = {
                        'name': account.code + ' ' + account.name,
                        'balance': value['balance'] * float(report.sign) or 0.0,
                        'type': 'account',
                        'level': report.display_detail == 'detail_with_hierarchy' and 4,
                        'account_type': account.account_type,
                    }

                    if data['debit_credit']:
                        vals['debit'] = value['debit']
                        vals['credit'] = value['credit']
                        if not self.env.company.currency_id.is_zero(vals['debit']) or \
                                not self.env.company.currency_id.is_zero(vals['credit']):
                            flag = True

                    if not self.env.company.currency_id.is_zero(vals['balance']):
                        flag = True

                    if data['enable_filter']:
                        vals['balance_cmp'] = value['comp_bal'] * float(report.sign)
                        if not self.env.company.currency_id.is_zero(vals['balance_cmp']):
                            flag = True

                    if flag:
                        sub_lines.append(vals)

                lines += sorted(sub_lines, key=lambda sub_line: sub_line['name'])

        return lines

    @api.model
    def _get_report_values(self, docids, data=None):
        """Override to pass analytic information"""
        result = super(ReportFinancial, self)._get_report_values(docids, data)

        # Add analytic account info
        if data['form'].get('analytic_account_id'):
            analytic_id = data['form']['analytic_account_id'][0] if isinstance(
                data['form']['analytic_account_id'], tuple) else data['form']['analytic_account_id']
            analytic_account = self.env['account.analytic.account'].browse(analytic_id)
            result['analytic_account'] = analytic_account

        result['analytic_filter'] = data['form'].get('analytic_filter', 'all')
        result['show_analytic_breakdown'] = data['form'].get('show_analytic_breakdown', False)

        return result

