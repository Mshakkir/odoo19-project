import time
from datetime import timedelta
from odoo import api, models, fields, _
from odoo.exceptions import UserError


class ReportCashbookAnalytic(models.AbstractModel):
    _name = 'report.om_cashbook_analytic.report_combined'
    _description = 'Cashbook with Analytic Accounts - Combined'

    def _get_account_move_entry(self, form_data, analytic_account_id=None):
        cr = self.env.cr
        MoveLine = self.env['account.move.line']

        # Determine posted/draft move filter
        target_move = "AND m.state = 'posted'" if form_data['target_move'] == 'posted' else ''

        # Filter only cash/bank journals
        cash_journal_ids = tuple(
            self.env['account.journal'].search([('type', 'in', ['cash', 'bank'])]).ids
        )
        if not cash_journal_ids:
            return {'debit': 0, 'credit': 0, 'balance': 0, 'lines': []}

        # Date range
        date_from = form_data['date_from']
        date_to = form_data['date_to']

        # Analytic filter
        analytic_filter = ""
        if analytic_account_id:
            analytic_filter = "AND l.analytic_distribution ? %s"
        elif form_data.get('analytic_account_ids'):
            analytic_ids = [str(aid) for aid in form_data['analytic_account_ids']]
            analytic_filter = "AND (" + " OR ".join(
                [f"l.analytic_distribution ? '{aid}'" for aid in analytic_ids]
            ) + ")"

        # SQL query
        sql = f"""
            SELECT 
                l.id AS lid,
                l.date AS ldate,
                j.code AS journal_code,
                acc.code AS account_code,
                acc.name AS account_name,
                p.name AS partner_name,
                l.ref AS ref,
                l.name AS label,
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
            AND l.date BETWEEN %s AND %s
            {target_move}
            {analytic_filter}
            ORDER BY l.date, j.code, l.id
        """

        where_params = [cash_journal_ids, date_from, date_to]
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
        if not data or not data.get('form'):
            raise UserError(_("Form content is missing, cannot print Cashbook."))

        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        form_data = data['form']

        # Prepare analytic names
        analytic_names = []
        analytic_accounts = []
        if form_data.get('analytic_account_ids'):
            analytic_accounts = self.env['account.analytic.account'].browse(form_data['analytic_account_ids'])
            analytic_names = [acc.name for acc in analytic_accounts]

        report_type = form_data.get('report_type', 'combined')
        records = []

        if report_type == 'separate' and analytic_accounts:
            # Separate report per analytic account
            for analytic_acc in analytic_accounts:
                res = self._get_account_move_entry(form_data, analytic_acc.id)
                if res['lines']:
                    records.append({
                        'analytic_account': analytic_acc.name,
                        'lines': res['lines'],
                        'debit': res['debit'],
                        'credit': res['credit'],
                        'balance': res['balance']
                    })
        else:
            # Combined report
            res = self._get_account_move_entry(form_data)
            if res['lines']:
                records.append({
                    'analytic_account': 'All Analytic Accounts',
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
            'date_from': form_data.get('date_from'),
            'date_to': form_data.get('date_to'),
        }
