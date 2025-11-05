# -*- coding: utf-8 -*-
import logging
import time
from datetime import timedelta
from odoo import api, models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ReportCashbookAnalytic(models.AbstractModel):
    _name = 'report.om_cashbook_analytic.report_combined'
    _description = 'Cashbook with Analytic Accounts - Combined'

    def _get_account_move_entry(self, form_data, analytic_account_id=None):
        cr = self.env.cr

        # Validate
        if not form_data:
            return {'debit': 0, 'credit': 0, 'balance': 0, 'lines': []}

        # Determine posted/draft move filter
        target_move = "AND m.state = 'posted'" if form_data.get('target_move') == 'posted' else ''

        # Get cash/bank journals
        cash_journal_ids_list = self.env['account.journal'].search([('type', 'in', ['cash', 'bank'])]).ids
        cash_journal_ids = tuple(cash_journal_ids_list) if cash_journal_ids_list else tuple([-1])
        if not cash_journal_ids_list:
            return {'debit': 0, 'credit': 0, 'balance': 0, 'lines': []}

        # Date range
        date_from = form_data.get('date_from')
        date_to = form_data.get('date_to')
        if not date_from or not date_to:
            raise UserError(_("Please provide both From and To dates."))

        # Account filter
        account_ids = form_data.get('account_ids') or []
        account_filter = ""
        # we'll add the account placeholder only if account_ids provided
        if account_ids:
            account_filter = " AND l.account_id IN %s"

        # Build analytic filter for JSON analytic_distribution (Odoo 17+)
        analytic_filter = ""
        params = [cash_journal_ids, date_from, date_to]

        # Debug: show incoming analytic data
        _logger.info("Report._get_account_move_entry called: analytic_account_id=%s, analytic_account_ids=%s",
                     analytic_account_id, form_data.get('analytic_account_ids'))

        if analytic_account_id:
            # single analytic (used for 'separate' reports)
            analytic_filter = " AND l.analytic_distribution ? %s"
            params.append(str(analytic_account_id))
        elif form_data.get('analytic_account_ids'):
            analytic_ids = form_data.get('analytic_account_ids') or []
            # build a group of OR conditions: l.analytic_distribution ? %s OR l.analytic_distribution ? %s ...
            analytic_filter = " AND (" + " OR ".join(
                ["l.analytic_distribution ? %s" for _ in analytic_ids]
            ) + ")"
            params.extend([str(aid) for aid in analytic_ids])

        # Add account_ids if selected
        if account_ids:
            params.append(tuple(account_ids))

        # Final SQL: note placeholders order must match params
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
                (
                    SELECT string_agg(aa.name, ', ')
                    FROM account_analytic_account aa
                    WHERE l.analytic_distribution ? CAST(aa.id AS TEXT)
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

        # Debug: log SQL and params lengths so we can check correctness in logs
        _logger.debug("Analytic Cashbook SQL params count=%s params=%s", len(params), params)

        # Execute safely
        cr.execute(sql, tuple(params))
        data = cr.dictfetchall()

        # compute totals
        debit = sum(line.get('debit', 0.0) for line in data)
        credit = sum(line.get('credit', 0.0) for line in data)
        balance = debit - credit

        _logger.info("Analytic Cashbook: fetched %s lines, debit=%s credit=%s", len(data), debit, credit)

        return {'debit': debit, 'credit': credit, 'balance': balance, 'lines': data}

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data or not data.get('form'):
            raise UserError(_("Form content is missing, cannot print Cashbook."))

        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        form_data = data['form']

        # Prepare analytic accounts and their names
        analytic_accounts = []
        analytic_names = []
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
            # Combined report (all analytics selected / none selected)
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
