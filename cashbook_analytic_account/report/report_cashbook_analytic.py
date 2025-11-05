import time
from odoo import api, models, _
from odoo.exceptions import UserError


class ReportCashBookAnalytic(models.AbstractModel):
    _inherit = 'report.om_account_daily_reports.report_cashbook'

    def _get_account_move_entry(self, accounts, init_balance, sortby, display_account):
        """Override to add analytic account filtering"""
        cr = self.env.cr
        MoveLine = self.env['account.move.line']
        move_lines = {x: [] for x in accounts.ids}

        # Get analytic account filter from context
        analytic_account_ids = self.env.context.get('analytic_account_ids', False)

        # Build the list of accounts if none selected
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

        # Handle case where still no accounts found
        if not accounts:
            return []

        # ---------- INITIAL BALANCE ----------
        if init_balance:
            init_tables, init_where_clause, init_where_params = MoveLine.with_context(
                date_from=self.env.context.get('date_from'),
                date_to=False,
                initial_bal=True
            )._query_get()
            init_wheres = [""]
            if init_where_clause.strip():
                init_wheres.append(init_where_clause.strip())

            # Add analytic account filter for initial balance
            if analytic_account_ids:
                init_wheres.append("l.analytic_distribution IS NOT NULL")

            init_filters = " AND ".join(init_wheres)
            filters = init_filters.replace('account_move_line__move_id', 'm').replace('account_move_line', 'l')

            sql = f"""
                SELECT 0 AS lid, 
                       l.account_id AS account_id, '' AS ldate, '' AS lcode, 
                       0.0 AS amount_currency,'' AS lref,'Initial Balance' AS lname, 
                       COALESCE(SUM(l.credit),0.0) AS credit,
                       COALESCE(SUM(l.debit),0.0) AS debit,
                       COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit),0) AS balance, 
                       '' AS lpartner_id,'' AS move_name, '' AS currency_code,NULL AS currency_id,'' AS partner_name,
                       '' AS mmove_id, '' AS invoice_id, '' AS invoice_type,'' AS invoice_number
                FROM account_move_line l 
                LEFT JOIN account_move m ON (l.move_id = m.id) 
                LEFT JOIN res_currency c ON (l.currency_id = c.id) 
                LEFT JOIN res_partner p ON (l.partner_id = p.id) 
                JOIN account_journal j ON (l.journal_id = j.id) 
                JOIN account_account acc ON (l.account_id = acc.id)
                WHERE l.account_id IN %s {filters}
            """

            # Add analytic account filtering for initial balance
            if analytic_account_ids:
                analytic_placeholders = ','.join(['%s'] * len(analytic_account_ids))
                sql += f" AND EXISTS (SELECT 1 FROM jsonb_each_text(l.analytic_distribution) WHERE key IN ({analytic_placeholders}))"
                params = (tuple(accounts.ids),) + tuple(init_where_params) + tuple(
                    str(aid) for aid in analytic_account_ids)
            else:
                params = (tuple(accounts.ids),) + tuple(init_where_params)

            sql += " GROUP BY l.account_id"

            cr.execute(sql, params)
            for row in cr.dictfetchall():
                move_lines[row.pop('account_id')].append(row)

        # ---------- REGULAR LINES ----------
        sql_sort = 'l.date, l.move_id'
        if sortby == 'sort_journal_partner':
            sql_sort = 'j.code, p.name, l.move_id'

        tables, where_clause, where_params = MoveLine._query_get()
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())

        # Add analytic account filter for regular lines
        if analytic_account_ids:
            wheres.append("l.analytic_distribution IS NOT NULL")

        filters = " AND ".join(wheres)
        filters = filters.replace('account_move_line__move_id', 'm').replace('account_move_line', 'l')

        sql = f"""
            SELECT l.id AS lid, l.account_id AS account_id, l.date AS ldate, j.code AS lcode,
                   l.currency_id, l.amount_currency, l.ref AS lref, l.name AS lname,
                   COALESCE(l.debit,0) AS debit, COALESCE(l.credit,0) AS credit,
                   COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) AS balance,
                   m.name AS move_name, c.symbol AS currency_code, p.name AS partner_name
            FROM account_move_line l
            JOIN account_move m ON (l.move_id=m.id)
            LEFT JOIN res_currency c ON (l.currency_id=c.id)
            LEFT JOIN res_partner p ON (l.partner_id=p.id)
            JOIN account_journal j ON (l.journal_id=j.id)
            JOIN account_account acc ON (l.account_id = acc.id)
            WHERE l.account_id IN %s {filters}
        """

        # Add analytic account filtering for regular lines
        if analytic_account_ids:
            analytic_placeholders = ','.join(['%s'] * len(analytic_account_ids))
            sql += f" AND EXISTS (SELECT 1 FROM jsonb_each_text(l.analytic_distribution) WHERE key IN ({analytic_placeholders}))"
            params = (tuple(accounts.ids),) + tuple(where_params) + tuple(str(aid) for aid in analytic_account_ids)
        else:
            params = (tuple(accounts.ids),) + tuple(where_params)

        sql += f"""
            GROUP BY l.id, l.account_id, l.date, j.code, l.currency_id, l.amount_currency, l.ref, l.name, m.name, c.symbol, p.name
            ORDER BY {sql_sort}
        """

        cr.execute(sql, params)

        for row in cr.dictfetchall():
            balance = 0
            for line in move_lines.get(row['account_id']):
                balance += line['debit'] - line['credit']
            row['balance'] += balance
            move_lines[row.pop('account_id')].append(row)

        # ---------- AGGREGATION ----------
        account_res = []
        for account in accounts:
            currency = account.currency_id or self.env.company.currency_id
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
            elif display_account == 'movement' and res.get('move_lines'):
                account_res.append(res)
            elif display_account == 'not_zero' and not currency.is_zero(res['balance']):
                account_res.append(res)
        return account_res

    @api.model
    def _get_report_values(self, docids, data=None):
        """Override to include analytic account information in report"""
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        init_balance = data['form'].get('initial_balance', True)
        display_account = data['form'].get('display_account')
        sortby = data['form'].get('sortby', 'sort_date')
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

        # Get analytic accounts for display
        analytic_account_ids = data['form'].get('analytic_account_ids', [])
        analytic_accounts = self.env['account.analytic.account'].browse(analytic_account_ids)
        analytic_names = ', '.join(analytic_accounts.mapped('name')) if analytic_accounts else 'All'

        record = self.with_context(
            data['form'].get('comparison_context', {})
        )._get_account_move_entry(accounts, init_balance, sortby, display_account)

        return {
            'doc_ids': docids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'Accounts': record,
            'print_journal': codes,
            'analytic_accounts': analytic_names,
        }