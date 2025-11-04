import time
from odoo import api, models, fields, _
from odoo.exceptions import UserError
from datetime import timedelta


class ReportCashbookAnalytic(models.AbstractModel):
    _name = 'report.om_cashbook_analytic.report_combined'
    _description = 'Cashbook with Analytic Accounts - Combined'

    def _get_account_move_entry(self, accounts, form_data, date, analytic_account_id=None):
        cr = self.env.cr
        MoveLine = self.env['account.move.line']

        if form_data['target_move'] == 'posted':
            target_move = "AND m.state = 'posted'"
        else:
            target_move = ''

        # Filter only cash/bank journals
        cash_journal_ids = tuple(
            self.env['account.journal'].search([('type', 'in', ['cash', 'bank'])]).ids
        )
        if not cash_journal_ids:
            return {'debit': 0, 'credit': 0, 'balance': 0, 'lines': []}

        analytic_filter = ""
        if analytic_account_id:
            analytic_filter = "AND l.analytic_distribution ? %s"
        elif form_data.get('analytic_account_ids'):
            analytic_ids = [str(aid) for aid in form_data['analytic_account_ids']]
            analytic_filter = "AND (" + " OR ".join(
                [f"l.analytic_distribution ? '{aid}'" for aid in analytic_ids]) + ")"

        sql = f"""
            SELECT 
                l.id AS lid, 
                l.date AS ldate,
                j.code AS lcode,
                acc.code AS account_code,
                acc.name AS account_name,
                p.name AS partner_name,
                l.ref AS lref,
                l.name AS lname,
                COALESCE(l.debit, 0.0) AS debit,
                COALESCE(l.credit, 0.0) AS credit,
                COALESCE(l.debit, 0) - COALESCE(l.credit, 0) AS balance,
                m.name AS move_name,
                aa.name AS analytic_account_name
            FROM account_move_line l
            JOIN account_move m ON (l.move_id = m.id)
            JOIN account_journal j ON (l.journal_id = j.id)
            JOIN account_account acc ON (l.account_id = acc.id)
            LEFT JOIN res_partner p ON (l.partner_id = p.id)
            LEFT JOIN account_analytic_account aa ON (l.analytic_distribution ? CAST(aa.id AS TEXT))
            WHERE l.journal_id IN %s
            AND l.date = %s
            {target_move}
            {analytic_filter}
            ORDER BY l.date, j.code
        """

        where_params = [cash_journal_ids, date]
        if analytic_account_id:
            where_params.append(str(analytic_account_id))

        cr.execute(sql, where_params)
        data = cr.dictfetchall()

        debit = sum(line['debit'] for line in data)
        credit = sum(line['credit'] for line in data)
        balance = debit - credit
        return {'debit': debit, 'credit': credit, 'balance': balance, 'lines': data}

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(_("Form content is missing, cannot print Cashbook."))

        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        form_data = data['form']

        date_from = fields.Date.from_string(form_data['date_from'])
        date_to = fields.Date.from_string(form_data['date_to'])

        analytic_names = []
        if form_data.get('analytic_account_ids'):
            analytic_accounts = self.env['account.analytic.account'].browse(
                form_data['analytic_account_ids']
            )
            analytic_names = [acc.name for acc in analytic_accounts]

        days_total = (date_to - date_from).days
        records = []

        for i in range(days_total + 1):
            date = date_from + timedelta(days=i)
            res = self._get_account_move_entry(self.env['account.account'].search([]), form_data, str(date))
            if res['lines']:
                records.append({
                    'date': date,
                    'lines': res['lines'],
                    'debit': res['debit'],
                    'credit': res['credit'],
                    'balance': res['balance']
                })

        return {
            'doc_ids': docids,
            'doc_model': model,
            'data': form_data,
            'docs': docs,
            'time': time,
            'records': records,
            'analytic_accounts': ', '.join(analytic_names) or 'All',
        }
