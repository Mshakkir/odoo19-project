import time
from odoo import api, models, _
from odoo.exceptions import UserError


class ReportBankBookAnalytic(models.AbstractModel):
    _name = 'report.bank_book_analytic.report_bankbook_analytic'
    _description = 'Bank Book with Analytic Accounts'
    _inherit = 'report.om_account_daily_reports.report_bankbook'

    def _get_account_move_entry(self, accounts, init_balance, sortby, display_account):
        cr = self.env.cr
        MoveLine = self.env['account.move.line']
        move_lines = {x: [] for x in accounts.ids}

        analytic_ids = self.env.context.get('analytic_account_ids', [])
        report_type = self.env.context.get('report_type', 'combined')
        show_without_analytic = self.env.context.get('show_without_analytic', True)

        # Get partner_ids - can be recordset, list, or string (from serialized context)
        partner_ids = self.env.context.get('partner_ids', [])
        partner_ids_list = []

        if partner_ids:
            # Handle different types
            if hasattr(partner_ids, 'ids'):
                # It's a recordset
                partner_ids_list = partner_ids.ids
            elif isinstance(partner_ids, (list, tuple)):
                # It's already a list
                partner_ids_list = list(partner_ids)
            elif isinstance(partner_ids, str):
                # It might be a string representation from serialization
                try:
                    import ast
                    partner_ids_list = ast.literal_eval(partner_ids)
                    if not isinstance(partner_ids_list, list):
                        partner_ids_list = [partner_ids_list]
                except:
                    partner_ids_list = []
            else:
                # Single ID
                partner_ids_list = [partner_ids]

        # Create a modified context with partner_ids as recordset for accounting_pdf_reports module
        modified_context = dict(self.env.context)
        if partner_ids_list:
            modified_context['partner_ids'] = self.env['res.partner'].browse(partner_ids_list)
        else:
            # Empty recordset if no partners selected
            modified_context['partner_ids'] = self.env['res.partner']

        # Initial balance
        if init_balance:
            init_tables, init_where_clause, init_where_params = MoveLine.with_context(
                modified_context,
                date_from=self.env.context.get('date_from'),
                date_to=False,
                initial_bal=True
            )._query_get()

            init_wheres = [""]
            if init_where_clause.strip():
                init_wheres.append(init_where_clause.strip())

            if analytic_ids:
                if show_without_analytic:
                    init_wheres.append(
                        "(l.analytic_distribution::text LIKE ANY(ARRAY[%s]) OR l.analytic_distribution IS NULL)")
                    init_where_params += ([f'%"{aid}%' for aid in analytic_ids],)
                else:
                    init_wheres.append("l.analytic_distribution::text LIKE ANY(ARRAY[%s])")
                    init_where_params += ([f'%"{aid}%' for aid in analytic_ids],)

            init_filters = " AND ".join(init_wheres)
            filters = init_filters.replace('account_move_line__move_id', 'm').replace('account_move_line', 'l')

            sql = ("""
                SELECT 0 AS lid,
                       l.account_id AS account_id,
                       '' AS ldate, '' AS lcode, 0.0 AS amount_currency,
                       '' AS lref, 'Initial Balance' AS lname,
                       COALESCE(SUM(l.credit), 0.0) AS credit,
                       COALESCE(SUM(l.debit), 0.0) AS debit,
                       COALESCE(SUM(l.debit), 0) - COALESCE(SUM(l.credit), 0) AS balance,
                       '' AS lpartner_id, '' AS move_name, '' AS currency_code,
                       NULL AS currency_id, '' AS partner_name,
                       '' AS analytic_account_id, '' AS analytic_account_name,
                       '' AS memo
                FROM account_move_line l
                LEFT JOIN account_move m ON (l.move_id = m.id)
                LEFT JOIN res_currency c ON (l.currency_id = c.id)
                LEFT JOIN res_partner p ON (l.partner_id = p.id)
                JOIN account_journal j ON (l.journal_id = j.id)
                JOIN account_account acc ON (l.account_id = acc.id)
                WHERE l.account_id IN %s """ + filters + ' GROUP BY l.account_id'
                   )

            params = (tuple(accounts.ids),) + tuple(init_where_params)
            cr.execute(sql, params)
            for row in cr.dictfetchall():
                move_lines[row.pop('account_id')].append(row)

        # Always sort by date, partner for bank book
        sql_sort = 'l.date, p.name, l.move_id'

        # Main query
        tables, where_clause, where_params = MoveLine.with_context(modified_context)._query_get()
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())

        if analytic_ids:
            if show_without_analytic:
                wheres.append("(l.analytic_distribution::text LIKE ANY(ARRAY[%s]) OR l.analytic_distribution IS NULL)")
                where_params += ([f'%"{aid}%' for aid in analytic_ids],)
            else:
                wheres.append("l.analytic_distribution::text LIKE ANY(ARRAY[%s])")
                where_params += ([f'%"{aid}%' for aid in analytic_ids],)

        filters = " AND ".join(wheres).replace('account_move_line__move_id', 'm').replace('account_move_line', 'l')

        if not accounts:
            journals = self.env['account.journal'].search([('type', '=', 'bank')])
            accounts = self.env['account.account']
            for journal in journals:
                for acc_out in journal.outbound_payment_method_line_ids:
                    if acc_out.payment_account_id:
                        accounts += acc_out.payment_account_id
                for acc_in in journal.inbound_payment_method_line_ids:
                    if acc_in.payment_account_id:
                        accounts += acc_in.payment_account_id

        # Join account.payment to fetch memo_new (the Memo field on payments)
        sql = ('''
                    SELECT l.id AS lid, l.account_id AS account_id, l.date AS ldate, j.code AS lcode,
                           l.currency_id, l.amount_currency, l.ref AS lref, l.name AS lname,
                           COALESCE(l.debit, 0) AS debit, COALESCE(l.credit, 0) AS credit,
                           COALESCE(SUM(l.debit), 0) - COALESCE(SUM(l.credit), 0) AS balance,
                           m.name AS move_name, c.symbol AS currency_code, p.name AS partner_name,
                           l.analytic_distribution, m.id AS move_id,
                           COALESCE(pay.memo_new, '') AS memo
                    FROM account_move_line l
                    JOIN account_move m ON (l.move_id = m.id)
                    LEFT JOIN res_currency c ON (l.currency_id = c.id)
                    LEFT JOIN res_partner p ON (l.partner_id = p.id)
                    JOIN account_journal j ON (l.journal_id = j.id)
                    JOIN account_account acc ON (l.account_id = acc.id)
                    LEFT JOIN account_payment pay ON (pay.move_id = m.id)
                    WHERE l.account_id IN %s ''' + filters + '''
                    GROUP BY l.id, l.account_id, l.date, j.code, l.currency_id, l.amount_currency,
                             l.ref, l.name, m.name, c.symbol, p.name, l.analytic_distribution, m.id,
                             pay.memo_new
                    ORDER BY ''' + sql_sort
               )

        params = (tuple(accounts.ids),) + tuple(where_params)
        cr.execute(sql, params)

        for row in cr.dictfetchall():
            balance = 0
            for line in move_lines.get(row['account_id']):
                balance += line['debit'] - line['credit']
            row['balance'] += balance

            analytic_info = self._get_analytic_info(row.get('analytic_distribution'))
            row['analytic_account_ids'] = analytic_info['ids']
            row['analytic_account_names'] = analytic_info['names']

            move_lines[row.pop('account_id')].append(row)

        account_res = []
        for account in accounts:
            currency = account.currency_id or self.env.company.currency_id
            res = {fn: 0.0 for fn in ['credit', 'debit', 'balance']}
            res.update({'code': account.code, 'name': account.name, 'move_lines': move_lines[account.id]})

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

    def _get_analytic_info(self, analytic_distribution):
        result = {'ids': [], 'names': ''}
        if not analytic_distribution:
            return result

        try:
            import json
            if isinstance(analytic_distribution, str):
                distribution = json.loads(analytic_distribution)
            else:
                distribution = analytic_distribution

            analytic_ids = [int(k) for k in distribution.keys()]
            if analytic_ids:
                analytics = self.env['account.analytic.account'].browse(analytic_ids)
                result['ids'] = analytic_ids
                # Format as comma-separated abbreviated names
                names = []
                for analytic in analytics:
                    name_parts = analytic.name.split(',')
                    abbreviated = ', '.join([part.strip() for part in name_parts])
                    names.append(abbreviated)
                result['names'] = ', '.join(names)
        except:
            pass

        return result

    def _group_by_analytic(self, account_res):
        grouped = {}
        without_analytic = []

        for account in account_res:
            account_data = account.copy()
            account_data['move_lines'] = []

            for line in account['move_lines']:
                if line.get('analytic_account_ids'):
                    for analytic_id in line['analytic_account_ids']:
                        if analytic_id not in grouped:
                            grouped[analytic_id] = []

                        found = False
                        for grp_acc in grouped[analytic_id]:
                            if grp_acc['code'] == account['code']:
                                grp_acc['move_lines'].append(line)
                                grp_acc['debit'] += line['debit']
                                grp_acc['credit'] += line['credit']
                                grp_acc['balance'] = line['balance']
                                found = True
                                break

                        if not found:
                            new_acc = account_data.copy()
                            new_acc['move_lines'] = [line]
                            new_acc['debit'] = line['debit']
                            new_acc['credit'] = line['credit']
                            new_acc['balance'] = line['balance']
                            grouped[analytic_id].append(new_acc)
                else:
                    found = False
                    for wo_acc in without_analytic:
                        if wo_acc['code'] == account['code']:
                            wo_acc['move_lines'].append(line)
                            wo_acc['debit'] += line['debit']
                            wo_acc['credit'] += line['credit']
                            wo_acc['balance'] = line['balance']
                            found = True
                            break

                    if not found:
                        new_acc = account_data.copy()
                        new_acc['move_lines'] = [line]
                        new_acc['debit'] = line['debit']
                        new_acc['credit'] = line['credit']
                        new_acc['balance'] = line['balance']
                        without_analytic.append(new_acc)

        return grouped, without_analytic

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        init_balance = data['form'].get('initial_balance', True)
        display_account = data['form'].get('display_account')
        sortby = 'sort_date'  # Always use date sorting

        analytic_ids = data['form'].get('analytic_account_ids', [])
        report_type = data['form'].get('report_type', 'combined')
        show_without_analytic = data['form'].get('show_without_analytic', True)

        # Get partner_ids from form data
        partner_ids_data = data['form'].get('partner_ids', [])
        partner_names = []
        if partner_ids_data:
            # If it's a recordset, get the IDs
            if hasattr(partner_ids_data, 'ids'):
                partner_ids_list = partner_ids_data.ids
            else:
                partner_ids_list = partner_ids_data if isinstance(partner_ids_data, list) else [partner_ids_data]

            if partner_ids_list:
                partners = self.env['res.partner'].browse(partner_ids_list)
                partner_names = partners.mapped('name')

        codes = []
        if data['form'].get('journal_ids', False):
            codes = [journal.code for journal in self.env['account.journal'].browse(data['form']['journal_ids'])]

        accounts = self.env['account.account'].browse(data['form']['account_ids'])
        if not accounts:
            journals = self.env['account.journal'].search([('type', '=', 'bank')])
            accounts = self.env['account.account']
            for journal in journals:
                for acc_out in journal.outbound_payment_method_line_ids:
                    if acc_out.payment_account_id:
                        accounts += acc_out.payment_account_id
                for acc_in in journal.inbound_payment_method_line_ids:
                    if acc_in.payment_account_id:
                        accounts += acc_in.payment_account_id

        record = self.with_context(data['form'].get('comparison_context', {}))._get_account_move_entry(
            accounts, init_balance, sortby, display_account
        )

        analytic_groups = {}
        without_analytic_data = []
        analytic_accounts = {}

        if report_type == 'separate':
            analytic_groups, without_analytic_data = self._group_by_analytic(record)

            if analytic_ids:
                for aa in self.env['account.analytic.account'].browse(analytic_ids):
                    analytic_accounts[aa.id] = aa.name
            else:
                all_ids = list(analytic_groups.keys())
                for aa in self.env['account.analytic.account'].browse(all_ids):
                    analytic_accounts[aa.id] = aa.name

        return {
            'doc_ids': docids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'Accounts': record,
            'print_journal': codes,
            'report_type': report_type,
            'analytic_groups': analytic_groups,
            'analytic_accounts': analytic_accounts,
            'without_analytic_data': without_analytic_data,
            'show_without_analytic': show_without_analytic,
            'analytic_account_ids': analytic_ids,
            'partner_ids': partner_ids_data,
            'partner_names': partner_names,
        }
