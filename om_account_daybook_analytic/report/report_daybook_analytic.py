import time
from odoo import api, models, fields, _
from odoo.exceptions import UserError
from datetime import timedelta


class ReportDayBookAnalytic(models.AbstractModel):
    # _name = 'report.om_account_daybook_analytic.report_daybook_analytic_combined'
    _name = 'report.om_daybook_analytic.report_combined'
    _description = 'Day Book with Analytic Accounts - Combined'


    def _get_account_move_entry(self, accounts, form_data, date, analytic_account_id=None):
        """
        Get account move entries filtered by analytic account
        """
        cr = self.env.cr
        MoveLine = self.env['account.move.line']

        if form_data['target_move'] == 'posted':
            target_move = "AND m.state = 'posted'"
        else:
            target_move = ''

        # Build analytic filter
        analytic_filter = ""
        if analytic_account_id:
            analytic_filter = "AND l.analytic_distribution ? %s"
        elif form_data.get('analytic_account_ids') and form_data['report_type'] != 'all':
            # For combined report with multiple analytic accounts
            analytic_ids = [str(aid) for aid in form_data['analytic_account_ids']]
            analytic_filter = "AND (" + " OR ".join(
                [f"l.analytic_distribution ? '{aid}'" for aid in analytic_ids]) + ")"

        sql = """
            SELECT 0 AS lid, 
                  l.account_id AS account_id, 
                  l.date AS ldate, 
                  j.code AS lcode, 
                  l.amount_currency AS amount_currency,
                  l.ref AS lref,
                  l.name AS lname, 
                  COALESCE(l.credit, 0.0) AS credit,
                  COALESCE(l.debit, 0) AS debit,
                  COALESCE(l.debit, 0) - COALESCE(l.credit, 0) as balance, 
                  m.name AS move_name, 
                  c.symbol AS currency_code, 
                  p.name AS lpartner_id, 
                  m.id AS mmove_id,
                  l.analytic_distribution AS analytic_distribution,
                  aa.name AS analytic_account_name
            FROM 
              account_move_line l 
              LEFT JOIN account_move m ON (l.move_id = m.id) 
              LEFT JOIN res_currency c ON (l.currency_id = c.id) 
              LEFT JOIN res_partner p ON (l.partner_id = p.id) 
              JOIN account_journal j ON (l.journal_id = j.id) 
              JOIN account_account acc ON (l.account_id = acc.id)
              LEFT JOIN account_analytic_account aa ON (l.analytic_distribution ? CAST(aa.id AS TEXT))
            WHERE 
              l.account_id IN %s 
              AND l.journal_id IN %s """ + target_move + """
              AND l.date = %s
              """ + analytic_filter + """
            GROUP BY 
              l.id, 
              l.account_id, 
              l.date, 
              m.name, 
              m.id, 
              p.name, 
              c.symbol, 
              j.code, 
              l.ref,
              l.analytic_distribution,
              aa.name
            ORDER BY 
              l.date DESC
        """

        where_params = [tuple(accounts.ids), tuple(form_data['journal_ids']), date]
        if analytic_account_id:
            where_params.append(str(analytic_account_id))

        cr.execute(sql, where_params)
        data = cr.dictfetchall()

        res = {}
        debit = credit = balance = 0.00
        for line in data:
            debit += line['debit']
            credit += line['credit']
            balance += line['balance']

        res['debit'] = debit
        res['credit'] = credit
        res['balance'] = balance
        res['lines'] = data
        return res

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        form_data = data['form']

        date_from = fields.Date.from_string(form_data['date_from'])
        date_to = fields.Date.from_string(form_data['date_to'])

        codes = []
        if data['form'].get('journal_ids', False):
            codes = [journal.code for journal in
                     self.env['account.journal'].browse(data['form']['journal_ids'])]

        # Get analytic account names
        analytic_names = []
        if form_data.get('analytic_account_ids') and form_data.get('report_type') != 'all':
            analytic_accounts = self.env['account.analytic.account'].browse(
                form_data['analytic_account_ids']
            )
            analytic_names = [acc.name for acc in analytic_accounts]

        accounts = self.env['account.account'].search([])
        dates = []
        record = []
        days_total = date_to - date_from

        for day in range(days_total.days + 1):
            dates.append(date_from + timedelta(days=day))

        for date in dates:
            date_data = str(date)
            accounts_res = self.with_context(
                data['form'].get('comparison_context', {})
            )._get_account_move_entry(accounts, form_data, date_data)

            if accounts_res['lines']:
                record.append({
                    'date': date,
                    'debit': accounts_res['debit'],
                    'credit': accounts_res['credit'],
                    'balance': accounts_res['balance'],
                    'move_lines': accounts_res['lines']
                })

        return {
            'doc_ids': docids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'Accounts': record,
            'print_journal': codes,
            'analytic_accounts': ', '.join(analytic_names) if analytic_names else 'All',
            'report_type': form_data.get('report_type', 'combined'),
        }


class ReportDayBookAnalyticSeparate(models.AbstractModel):
    # _name = 'report.om_account_daybook_analytic.report_daybook_analytic_separate'
    _name = 'report.om_daybook_analytic.report_separate'
    _description = 'Day Book with Analytic Accounts - Separate'

    def _get_account_move_entry(self, accounts, form_data, date, analytic_account_id):
        """
        Get account move entries for a specific analytic account
        """
        cr = self.env.cr

        if form_data['target_move'] == 'posted':
            target_move = "AND m.state = 'posted'"
        else:
            target_move = ''

        sql = """
            SELECT 0 AS lid, 
                  l.account_id AS account_id, 
                  l.date AS ldate, 
                  j.code AS lcode, 
                  l.amount_currency AS amount_currency,
                  l.ref AS lref,
                  l.name AS lname, 
                  COALESCE(l.credit, 0.0) AS credit,
                  COALESCE(l.debit, 0) AS debit,
                  COALESCE(l.debit, 0) - COALESCE(l.credit, 0) as balance, 
                  m.name AS move_name, 
                  c.symbol AS currency_code, 
                  p.name AS lpartner_id, 
                  m.id AS mmove_id
            FROM 
              account_move_line l 
              LEFT JOIN account_move m ON (l.move_id = m.id) 
              LEFT JOIN res_currency c ON (l.currency_id = c.id) 
              LEFT JOIN res_partner p ON (l.partner_id = p.id) 
              JOIN account_journal j ON (l.journal_id = j.id) 
              JOIN account_account acc ON (l.account_id = acc.id)
            WHERE 
              l.account_id IN %s 
              AND l.journal_id IN %s """ + target_move + """
              AND l.date = %s
              AND l.analytic_distribution ? %s
            GROUP BY 
              l.id, 
              l.account_id, 
              l.date, 
              m.name, 
              m.id, 
              p.name, 
              c.symbol, 
              j.code, 
              l.ref
            ORDER BY 
              l.date DESC
        """

        where_params = (
            tuple(accounts.ids),
            tuple(form_data['journal_ids']),
            date,
            str(analytic_account_id)
        )
        cr.execute(sql, where_params)
        data = cr.dictfetchall()

        res = {}
        debit = credit = balance = 0.00
        for line in data:
            debit += line['debit']
            credit += line['credit']
            balance += line['balance']

        res['debit'] = debit
        res['credit'] = credit
        res['balance'] = balance
        res['lines'] = data
        return res

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        form_data = data['form']

        date_from = fields.Date.from_string(form_data['date_from'])
        date_to = fields.Date.from_string(form_data['date_to'])

        codes = []
        if data['form'].get('journal_ids', False):
            codes = [journal.code for journal in
                     self.env['account.journal'].browse(data['form']['journal_ids'])]

        accounts = self.env['account.account'].search([])

        # Get analytic accounts
        analytic_accounts = self.env['account.analytic.account'].browse(
            form_data.get('analytic_account_ids', [])
        )

        # Build separate report for each analytic account
        analytic_reports = []
        for analytic_account in analytic_accounts:
            dates = []
            record = []
            days_total = date_to - date_from

            for day in range(days_total.days + 1):
                dates.append(date_from + timedelta(days=day))

            for date in dates:
                date_data = str(date)
                accounts_res = self._get_account_move_entry(
                    accounts, form_data, date_data, analytic_account.id
                )

                if accounts_res['lines']:
                    record.append({
                        'date': date,
                        'debit': accounts_res['debit'],
                        'credit': accounts_res['credit'],
                        'balance': accounts_res['balance'],
                        'move_lines': accounts_res['lines']
                    })

            if record:  # Only add if there are records
                analytic_reports.append({
                    'analytic_account': analytic_account.name,
                    'analytic_account_code': analytic_account.code or '',
                    'records': record
                })

        return {
            'doc_ids': docids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'print_journal': codes,
            'analytic_reports': analytic_reports,
        }