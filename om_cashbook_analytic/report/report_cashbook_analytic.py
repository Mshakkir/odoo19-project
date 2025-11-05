# -*- coding: utf-8 -*-
import logging
import time
from odoo import api, models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ReportCashbookAnalytic(models.AbstractModel):
    _name = 'report.om_cashbook_analytic.report_combined'
    _description = 'Cashbook with Analytic Accounts - Combined'

    def _get_account_move_entry(self, form_data, analytic_account_id=None):
        cr = self.env.cr

        if not form_data:
            return {'debit': 0, 'credit': 0, 'balance': 0, 'lines': []}

        target_move = "AND m.state = 'posted'" if form_data.get('target_move') == 'posted' else ''

        # Cash/bank journals
        cash_journal_ids = self.env['account.journal'].search([('type', 'in', ['cash', 'bank'])]).ids
        if not cash_journal_ids:
            return {'debit': 0, 'credit': 0, 'balance': 0, 'lines': []}

        date_from = form_data.get('date_from')
        date_to = form_data.get('date_to')
        if not date_from or not date_to:
            raise UserError(_("Please provide both From and To dates."))

        account_ids = form_data.get('account_ids') or []
        account_filter = "AND l.account_id IN %s" if account_ids else ""

        params = [tuple(cash_journal_ids), date_from, date_to]

        # --- Analytic filter ---
        analytic_filter = ""
        if analytic_account_id:
            analytic_filter = "AND l.analytic_distribution ? %s"
            params.append(str(analytic_account_id))
        elif form_data.get('analytic_account_ids'):
            analytic_ids = form_data['analytic_account_ids']
            analytic_filter = "AND (" + " OR ".join(["l.analytic_distribution ? %s" for _ in analytic_ids]) + ")"
            params.extend([str(aid) for aid in analytic_ids])

        if account_ids:
            params.append(tuple(account_ids))

        # --- SQL Query ---
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
                (COALESCE(l.debit, 0.0) - COALESCE(l.credit, 0.0)) AS balance,
                m.name AS move_name,
                (
                    SELECT string_agg(aa.name, ', ')
                    FROM account_analytic_account aa
                    WHERE l.analytic_distribution ? CAST(aa.id AS TEXT)
                ) AS analytic_account_name
            FROM account_move_line l
            JOIN account_move m ON l.move_id = m.id
            JOIN account_journal j ON l.journal_id = j.id
            JOIN account_account acc ON l.account_id = acc.id
            LEFT JOIN res_partner p ON l.partner_id = p.id
            WHERE l.journal_id IN %s
              AND l.date BETWEEN %s AND %s
              {target_move}
              {analytic_filter}
              {account_filter}
            ORDER BY l.date, j.code, l.id
        """

        _logger.warning(">>> ANALYTIC SQL: %s", sql)
        _logger.warning(">>> SQL PARAMS: %s", params)

        cr.execute(sql, tuple(params))
        data = cr.dictfetchall()

        debit = sum(line.get('debit', 0.0) for line in data)
        credit = sum(line.get('credit', 0.0) for line in data)
        balance = debit - credit

        _logger.info("Fetched %s lines (analytic=%s)", len(data), analytic_account_id)

        return {'debit': debit, 'credit': credit, 'balance': balance, 'lines': data}

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data or not data.get('form'):
            raise UserError(_("Form content is missing."))

        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        form_data = data['form']

        analytic_accounts = self.env['account.analytic.account'].browse(form_data.get('analytic_account_ids', []))
        report_type = form_data.get('report_type', 'combined')

        records = []
        if report_type == 'separate' and analytic_accounts:
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
            'records': records,
            'analytic_accounts': ', '.join(analytic_accounts.mapped('name')) or 'All',
            'date_from': form_data.get('date_from'),
            'date_to': form_data.get('date_to'),
            'time': time,
        }
