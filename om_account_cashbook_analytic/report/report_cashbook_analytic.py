import time
from odoo import api, models, _
from odoo.exceptions import UserError


class ReportCashBookAnalytic(models.AbstractModel):
    _name = 'report.account_cashbook_analytic.report_cashbook_analytic'
    _description = 'Cash Book with Analytic Accounts'
    _inherit = 'report.om_account_daily_reports.report_cashbook'

    def _get_account_move_entry(self, accounts, init_balance, sortby, display_account):
        """
        Override to add analytic account filtering and grouping
        """
        cr = self.env.cr
        MoveLine = self.env['account.move.line']
        move_lines = {x: [] for x in accounts.ids}

        # Get analytic account filter from context
        analytic_account_ids = self.env.context.get('analytic_account_ids', [])
        report_type = self.env.context.get('report_type', 'combined')
        group_by_analytic = self.env.context.get('group_by_analytic', True)

        # Build analytic filter
        analytic_filter = ""
        analytic_params = []
        if analytic_account_ids:
            analytic_filter = " AND l.analytic_distribution IS NOT NULL"
            # For filtering by specific analytic accounts, we'll do it in post-processing
            # since analytic_distribution is a JSON field

        # Prepare initial sql query and Get the initial move lines
        if init_balance:
            init_tables, init_where_clause, init_where_params = MoveLine.with_context(
                date_from=self.env.context.get('date_from'),
                date_to=False,
                initial_bal=True
            )._query_get()

            init_wheres = [""]
            if init_where_clause.strip():
                init_wheres.append(init_where_clause.strip())
            init_filters = " AND ".join(init_wheres)
            filters = init_filters.replace('account_move_line__move_id', 'm').replace('account_move_line', 'l')

            sql = ("""
                SELECT 0 AS lid, 
                l.account_id AS account_id, '' AS ldate, '' AS lcode, 
                0.0 AS amount_currency,'' AS lref,'Initial Balance' AS lname, 
                COALESCE(SUM(l.credit),0.0) AS credit,COALESCE(SUM(l.debit),0.0) AS debit,
                COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit),0) as balance, 
                '' AS lpartner_id,'' AS move_name, '' AS currency_code,NULL AS currency_id,
                '' AS partner_name, '' AS mmove_id, '' AS invoice_id, '' AS invoice_type,
                '' AS invoice_number, '' AS analytic_distribution, '' AS analytic_account_name
                FROM account_move_line l 
                LEFT JOIN account_move m ON (l.move_id = m.id) 
                LEFT JOIN res_currency c ON (l.currency_id = c.id) 
                LEFT JOIN res_partner p ON (l.partner_id = p.id) 
                JOIN account_journal j ON (l.journal_id = j.id) 
                JOIN account_account acc ON (l.account_id = acc.id) 
                WHERE l.account_id IN %s""" + filters + analytic_filter + ' GROUP BY l.account_id')

            params = (tuple(accounts.ids),) + tuple(init_where_params) + tuple(analytic_params)
            cr.execute(sql, params)

            for row in cr.dictfetchall():
                move_lines[row.pop('account_id')].append(row)

        sql_sort = 'l.date, l.move_id'
        if sortby == 'sort_journal_partner':
            sql_sort = 'j.code, p.name, l.move_id'

        # Prepare sql query base on selected parameters from wizard
        tables, where_clause, where_params = MoveLine._query_get()
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres)
        filters = filters.replace('account_move_line__move_id', 'm').replace('account_move_line', 'l')

        if not accounts:
            journals = self.env['account.journal'].search([('type', '=', 'cash')])
            accounts = self.env['account.account']
            for journal in journals:
                for acc_out in journal.outbound_payment_method_line_ids:
                    if acc_out.payment_account_id:
                        accounts += acc_out.payment_account_id
                for acc_in in journal.inbound_payment_method_line_ids:
                    if acc_in.payment_account_id:
                        accounts += acc_in.payment_account_id

        # Modified SQL to include analytic_distribution
        sql = ('''SELECT l.id AS lid, l.account_id AS account_id, l.date AS ldate, 
                  j.code AS lcode, l.currency_id, l.amount_currency, l.ref AS lref, 
                  l.name AS lname, COALESCE(l.debit,0) AS debit, COALESCE(l.credit,0) AS credit, 
                  COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) AS balance,
                  m.name AS move_name, c.symbol AS currency_code, p.name AS partner_name,
                  l.analytic_distribution AS analytic_distribution
                  FROM account_move_line l
                  JOIN account_move m ON (l.move_id=m.id)
                  LEFT JOIN res_currency c ON (l.currency_id=c.id)
                  LEFT JOIN res_partner p ON (l.partner_id=p.id)
                  JOIN account_journal j ON (l.journal_id=j.id)
                  JOIN account_account acc ON (l.account_id = acc.id) 
                  WHERE l.account_id IN %s ''' + filters + analytic_filter +
               ''' GROUP BY l.id, l.account_id, l.date, j.code, l.currency_id, 
                   l.amount_currency, l.ref, l.name, m.name, c.symbol, p.name, 
                   l.analytic_distribution ORDER BY ''' + sql_sort)

        params = (tuple(accounts.ids),) + tuple(where_params) + tuple(analytic_params)
        cr.execute(sql, params)

        # Process rows and filter by analytic accounts if specified
        for row in cr.dictfetchall():
            # Filter by analytic accounts if specified
            if analytic_account_ids and row.get('analytic_distribution'):
                import json
                try:
                    analytic_dist = json.loads(row['analytic_distribution'])
                    # Check if any of the specified analytic accounts are in the distribution
                    has_matching_analytic = any(
                        str(acc_id) in analytic_dist
                        for acc_id in analytic_account_ids
                    )
                    if not has_matching_analytic:
                        continue
                except:
                    continue
            elif analytic_account_ids and not row.get('analytic_distribution'):
                # Skip lines without analytic accounts if filter is specified
                continue

            # Get analytic account names for display
            if row.get('analytic_distribution'):
                import json
                try:
                    analytic_dist = json.loads(row['analytic_distribution'])
                    analytic_names = []
                    for acc_id in analytic_dist.keys():
                        analytic_acc = self.env['account.analytic.account'].browse(int(acc_id))
                        if analytic_acc.exists():
                            analytic_names.append(analytic_acc.name)
                    row['analytic_account_name'] = ', '.join(analytic_names)
                except:
                    row['analytic_account_name'] = ''
            else:
                row['analytic_account_name'] = ''

            balance = 0
            for line in move_lines.get(row['account_id']):
                balance += line['debit'] - line['credit']
            row['balance'] += balance
            move_lines[row.pop('account_id')].append(row)

        # Calculate the debit, credit and balance for Accounts
        account_res = []
        for account in accounts:
            currency = account.currency_id and account.currency_id or self.env.company.currency_id
            res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
            res['code'] = account.code
            res['name'] = account.name
            res['move_lines'] = move_lines[account.id]

            for line in res.get('move_lines'):
                res['debit'] += line['debit']
                res['credit'] += line['credit']
                res['balance'] = line['balance']

            if display_account == 'all':
                account_res.append(res)
            if display_account == 'movement' and res.get('move_lines'):
                account_res.append(res)
            if display_account == 'not_zero' and not currency.is_zero(res['balance']):
                account_res.append(res)

        return account_res

    def _group_by_analytic_account(self, account_res):
        """
        Group account results by analytic account
        """
        grouped_data = {}
        no_analytic_key = 'no_analytic'

        for account in account_res:
            for line in account['move_lines']:
                analytic_name = line.get('analytic_account_name', '')

                if not analytic_name:
                    key = no_analytic_key
                    display_name = 'No Analytic Account'
                else:
                    key = analytic_name
                    display_name = analytic_name

                if key not in grouped_data:
                    grouped_data[key] = {
                        'analytic_name': display_name,
                        'accounts': {}
                    }

                account_key = f"{account['code']}_{account['name']}"
                if account_key not in grouped_data[key]['accounts']:
                    grouped_data[key]['accounts'][account_key] = {
                        'code': account['code'],
                        'name': account['name'],
                        'debit': 0.0,
                        'credit': 0.0,
                        'balance': 0.0,
                        'move_lines': []
                    }

                grouped_data[key]['accounts'][account_key]['move_lines'].append(line)
                grouped_data[key]['accounts'][account_key]['debit'] += line['debit']
                grouped_data[key]['accounts'][account_key]['credit'] += line['credit']
                grouped_data[key]['accounts'][account_key]['balance'] = line['balance']

        # Convert to list format
        result = []
        for key, data in grouped_data.items():
            result.append({
                'analytic_name': data['analytic_name'],
                'accounts': list(data['accounts'].values())
            })

        return result

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        init_balance = data['form'].get('initial_balance', True)
        display_account = data['form'].get('display_account')
        sortby = data['form'].get('sortby', 'sort_date')
        report_type = data['form'].get('report_type', 'combined')
        group_by_analytic = data['form'].get('group_by_analytic', True)

        codes = []
        if data['form'].get('journal_ids', False):
            codes = [journal.code for journal in
                     self.env['account.journal'].browse(data['form']['journal_ids'])]

        account_ids = data['form']['account_ids']
        accounts = self.env['account.account'].browse(account_ids)

        if not accounts:
            journals = self.env['account.journal'].search([('type', '=', 'cash')])
            accounts = self.env['account.account']
            for journal in journals:
                for acc_out in journal.outbound_payment_method_line_ids:
                    if acc_out.payment_account_id:
                        accounts += acc_out.payment_account_id
                for acc_in in journal.inbound_payment_method_line_ids:
                    if acc_in.payment_account_id:
                        accounts += acc_in.payment_account_id

        record = self.with_context(
            data['form'].get('comparison_context', {})
        )._get_account_move_entry(accounts, init_balance, sortby, display_account)

        # Group by analytic account if requested
        analytic_grouped_data = None
        if group_by_analytic and report_type == 'combined':
            analytic_grouped_data = self._group_by_analytic_account(record)

        # Get analytic account names for display
        analytic_account_names = []
        if data['form'].get('analytic_account_ids'):
            analytic_accounts = self.env['account.analytic.account'].browse(
                data['form']['analytic_account_ids']
            )
            analytic_account_names = [acc.name for acc in analytic_accounts]

        return {
            'doc_ids': docids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'Accounts': record,
            'print_journal': codes,
            'analytic_grouped_data': analytic_grouped_data,
            'analytic_account_names': analytic_account_names,
            'report_type': report_type,
            'group_by_analytic': group_by_analytic,
        }