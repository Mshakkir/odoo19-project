# -*- coding: utf-8 -*-
import logging
import time
from odoo import api, models, _, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ReportCashbookAnalytic(models.AbstractModel):
    _name = 'report.om_cashbook_analytic.report_combined'
    _description = 'Cashbook with Analytic Accounts - Combined and Separate'

    def _get_account_move_entry(self, form_data, analytic_account_id=None):
        cr = self.env.cr

        if not form_data:
            return {'debit': 0, 'credit': 0, 'balance': 0, 'lines': []}

        # Journal filter (only Cash and Bank)
        cash_journal_ids = self.env['account.journal'].search([('type', 'in', ['cash', 'bank'])]).ids
        if not cash_journal_ids:
            _logger.warning("No cash/bank journals found!")
            return {'debit': 0, 'credit': 0, 'balance': 0, 'lines': []}

        # Prepare filters
        date_from = form_data.get('date_from')
        date_to = form_data.get('date_to')
        if not date_from or not date_to:
            raise UserError(_("Please provide both From and To dates."))

        target_move = "AND m.state = 'posted'" if form_data.get('target_move') == 'posted' else ''
        account_ids = form_data.get('account_ids') or []

        # Start parameter list
        params = [tuple(cash_journal_ids), date_from, date_to]

        # Analytic account filter - FIXED LOGIC
        analytic_filter = ""
        if analytic_account_id:
            # For separate reports: only get lines with THIS specific analytic account
            _logger.warning(">>> Filtering for analytic_account_id: %s", analytic_account_id)
            analytic_filter = """
                AND l.analytic_distribution IS NOT NULL 
                AND l.analytic_distribution ? %s
                AND (l.analytic_distribution->>%s)::numeric > 0
            """
            params.extend([str(analytic_account_id), str(analytic_account_id)])
        elif form_data.get('analytic_account_ids'):
            # For combined with filter: get lines with ANY of the selected analytic accounts
            analytic_ids = form_data.get('analytic_account_ids') or []
            if analytic_ids:
                _logger.warning(">>> Filtering for multiple analytic_account_ids: %s", analytic_ids)
                conditions = []
                for aid in analytic_ids:
                    conditions.append("(l.analytic_distribution ? %s AND (l.analytic_distribution->>%s)::numeric > 0)")
                    params.extend([str(aid), str(aid)])
                analytic_filter = " AND (" + " OR ".join(conditions) + ")"

        # Account filter
        account_filter = ""
        if account_ids:
            account_filter = " AND l.account_id IN %s"
            params.append(tuple(account_ids))

        # Final SQL
        sql_query = f"""
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
                (
                    SELECT string_agg(aa.name, ', ')
                    FROM account_analytic_account aa
                    WHERE l.analytic_distribution ? CAST(aa.id AS TEXT)
                      AND (l.analytic_distribution->>CAST(aa.id AS TEXT))::numeric > 0
                ) AS analytic_account_name
            FROM account_move_line l
            JOIN account_move m ON (l.move_id = m.id)
            JOIN account_journal j ON (l.journal_id = j.id)
            JOIN account_account acc ON (l.account_id = acc.id)
            LEFT JOIN res_partner p ON (l.partner_id = p.id)
            WHERE l.journal_id IN %s
              AND l.date BETWEEN %s AND %s
              {target_move}
              {analytic_filter}
              {account_filter}
            ORDER BY l.date, j.code, l.id
        """

        # 🧾 Log SQL + parameters for debugging
        _logger.warning(">>> CASHBOOK SQL QUERY:\n%s", sql_query)
        _logger.warning(">>> CASHBOOK SQL PARAMS: %s", params)

        # Execute safely
        cr.execute(sql_query, tuple(params))
        lines = cr.dictfetchall()

        debit = sum(line.get('debit', 0.0) for line in lines)
        credit = sum(line.get('credit', 0.0) for line in lines)
        balance = debit - credit

        _logger.warning(">>> Fetched %s lines (debit=%s, credit=%s) for analytic_id=%s",
                        len(lines), debit, credit, analytic_account_id)

        return {'debit': debit, 'credit': credit, 'balance': balance, 'lines': lines}

    @api.model
    def _get_report_values(self, docids, data=None):
        _logger.warning(">>> _get_report_values CALLED!")
        _logger.warning(">>> docids: %s", docids)
        _logger.warning(">>> data: %s", data)

        if not data or not data.get('form'):
            raise UserError(_("Form content is missing, cannot print Cashbook."))

        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        form_data = data['form']

        _logger.warning(">>> form_data: %s", form_data)

        analytic_accounts = []
        analytic_names = []
        if form_data.get('analytic_account_ids'):
            analytic_accounts = self.env['account.analytic.account'].browse(form_data['analytic_account_ids'])
            analytic_names = [acc.name for acc in analytic_accounts]
            _logger.warning(">>> Analytic accounts to process: %s", analytic_names)

        report_type = form_data.get('report_type', 'combined')
        _logger.warning(">>> Report Type: %s", report_type)
        records = []

        if report_type == 'separate' and analytic_accounts:
            # Separate per analytic account
            _logger.warning(">>> Generating SEPARATE reports for %s analytic accounts", len(analytic_accounts))
            for analytic_acc in analytic_accounts:
                _logger.warning(">>> Processing analytic account: %s (ID: %s)", analytic_acc.name, analytic_acc.id)
                res = self._get_account_move_entry(form_data, analytic_acc.id)
                # Always add, even if no lines (to show empty report)
                records.append({
                    'analytic_account': analytic_acc.name,
                    'lines': res['lines'],
                    'debit': res['debit'],
                    'credit': res['credit'],
                    'balance': res['balance']
                })
                _logger.warning(">>> Added record for %s with %s lines", analytic_acc.name, len(res['lines']))
        else:
            # Combined
            _logger.warning(">>> Generating COMBINED report")
            res = self._get_account_move_entry(form_data)
            records.append({
                'analytic_account': 'All Analytic Accounts',
                'lines': res['lines'],
                'debit': res['debit'],
                'credit': res['credit'],
                'balance': res['balance']
            })
            _logger.warning(">>> Added combined record with %s lines", len(res['lines']))

        _logger.warning(">>> Total records to display: %s", len(records))

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