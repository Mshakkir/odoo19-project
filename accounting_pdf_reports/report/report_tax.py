from odoo import api, models, _
from odoo.exceptions import UserError
from collections import defaultdict

class ReportTax(models.AbstractModel):
    _name = 'report.accounting_pdf_reports.report_tax'
    _description = 'Tax Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))
        form = data.get('form') or {}
        report_option = form.get('report_option', 'normal')
        date_from = form.get('date_from')
        date_to = form.get('date_to')
        target_move = form.get('target_move', 'posted')

        res_company = self.env.company

        if report_option == 'normal':
            lines = self.get_summary_lines(form)
        else:
            lines = self.get_detail_lines(form)

        return {
            'data': form,
            'lines': lines,
            'res_company': res_company,
            'report_option': report_option,
        }

    # --- existing helper SQLs unchanged ---
    def _sql_from_amls_one(self):
        sql = """SELECT "account_move_line".tax_line_id, COALESCE(SUM("account_move_line".debit-"account_move_line".credit), 0)
                    FROM %s
                    WHERE %s GROUP BY "account_move_line".tax_line_id"""
        return sql

    def _sql_from_amls_two(self):
        sql = """SELECT r.account_tax_id, COALESCE(SUM("account_move_line".debit-"account_move_line".credit), 0)
                 FROM %s
                 INNER JOIN account_move_line_account_tax_rel r ON ("account_move_line".id = r.account_move_line_id)
                 INNER JOIN account_tax t ON (r.account_tax_id = t.id)
                 WHERE %s GROUP BY r.account_tax_id"""
        return sql

    def _compute_from_amls(self, options, taxes):
        sql = self._sql_from_amls_one()
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        query = sql % (tables, where_clause)
        self.env.cr.execute(query, where_params)
        results = self.env.cr.fetchall()
        for result in results:
            if result[0] in taxes:
                taxes[result[0]]['tax'] = abs(result[1])

        sql2 = self._sql_from_amls_two()
        query = sql2 % (tables, where_clause)
        self.env.cr.execute(query, where_params)
        results = self.env.cr.fetchall()
        for result in results:
            if result[0] in taxes:
                taxes[result[0]]['net'] = abs(result[1])

    # --- summary (normal) lines: same as your get_lines() but renamed ---
    def get_summary_lines(self, options):
        taxes = {}
        for tax in self.env['account.tax'].search([('type_tax_use', '!=', 'none')]):
            # If tax has children, pick child items for break down (keep original logic)
            if tax.children_tax_ids:
                for child in tax.children_tax_ids:
                    if child.type_tax_use != 'none':
                        continue
                    taxes[child.id] = {'tax': 0, 'net': 0, 'name': child.name, 'type': tax.type_tax_use, 'tax_id': child.id}
            else:
                taxes[tax.id] = {'tax': 0, 'net': 0, 'name': tax.name, 'type': tax.type_tax_use, 'tax_id': tax.id}

        self.with_context(date_from=options['date_from'], date_to=options['date_to'],
                          state=options['target_move'],
                          strict_range=True)._compute_from_amls(options, taxes)

        groups = dict((tp, []) for tp in ['sale', 'purchase'])
        for tax in taxes.values():
            if tax['tax'] or tax['net']:
                groups[tax['type']].append(tax)
        return groups

    # --- detail lines: return mapping by tax -> list of details (account_move_line level summary) ---
    def get_detail_lines(self, options):
        # We'll produce a dict: {'sale': [ {tax:..., details:[{account_name, partner, move, debit, credit, balance}, ...]}, ... ], 'purchase': [...] }
        date_from = options.get('date_from')
        date_to = options.get('date_to')
        target_move = options.get('target_move', 'posted')

        # Build domain for account.move.line using Odoo's _query_get
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        # Compose SQL to fetch move lines grouped by tax and account
        # Note: this SQL will pick rows that are linked to a tax (via account_move_line_account_tax_rel)
        sql = """
            SELECT r.account_tax_id AS tax_id,
                   aml.account_id,
                   COALESCE(SUM(aml.debit),0) AS debit,
                   COALESCE(SUM(aml.credit),0) AS credit
            FROM %s aml
            INNER JOIN account_move_line_account_tax_rel r ON (aml.id = r.account_move_line_id)
            WHERE %s
            GROUP BY r.account_tax_id, aml.account_id
            ORDER BY r.account_tax_id
        """ % (tables, where_clause)

        self.env.cr.execute(sql, where_params)
        rows = self.env.cr.fetchall()

        # rows: [(tax_id, account_id, debit, credit), ...]
        # Build dictionary
        tax_map = {}
        for tax_id, account_id, debit, credit in rows:
            if tax_id not in tax_map:
                tax_rec = self.env['account.tax'].browse(tax_id)
                tax_map[tax_id] = {
                    'tax_id': tax_id,
                    'tax_name': tax_rec.name or '',
                    'type': tax_rec.type_tax_use or '',
                    'total_net': 0.0,
                    'total_tax': 0.0,
                    'details': []
                }
            account = self.env['account.account'].browse(account_id)
            balance = float(debit or 0.0) - float(credit or 0.0)
            tax_map[tax_id]['details'].append({
                'account_id': account_id,
                'account_code': account.code or '',
                'account_name': account.name or '',
                'debit': float(debit or 0.0),
                'credit': float(credit or 0.0),
                'balance': balance
            })
            tax_map[tax_id]['total_net'] += abs(balance)

        # We also need tax amounts separately (compute using your existing SQLs)
        taxes_data = {}
        for tax in self.env['account.tax'].search([('type_tax_use','!=','none')]):
            taxes_data[tax.id] = {'tax': 0.0, 'net': 0.0, 'name': tax.name, 'type': tax.type_tax_use}

        # compute totals per tax (reuse compute)
        self.with_context(date_from=options['date_from'], date_to=options['date_to'],
                          state=options['target_move'],
                          strict_range=True)._compute_from_amls(options, taxes_data)

        # attach tax amount to our tax_map
        for tax_id, d in tax_map.items():
            d['total_tax'] = taxes_data.get(tax_id, {}).get('tax', 0.0)
            d['total_net'] = taxes_data.get(tax_id, {}).get('net', d.get('total_net', 0.0))

        # group by sale/purchase type
        groups = dict((tp, []) for tp in ['sale', 'purchase'])
        for tax_id, d in tax_map.items():
            ttype = d.get('type') or 'sale'
            groups.setdefault(ttype, []).append(d)

        return groups
