# # -*- coding: utf-8 -*-
# import time
# from odoo import api, models, fields, _
# from odoo.exceptions import UserError
#
#
# class ReportPartnerLedgerCustom(models.AbstractModel):
#     _inherit = 'report.accounting_pdf_reports.report_partnerledger'
#     _description = 'Custom Partner Ledger Report'
#
#     def _lines(self, data, partner):
#         """
#         Override the _lines method to filter by analytic accounts
#         """
#         full_account = []
#         currency = self.env['res.currency']
#         query_get_data = self.env['account.move.line'].with_context(
#             data['form'].get('used_context', {})
#         )._query_get()
#         reconcile_clause = "" if data['form']['reconciled'] else ' AND "account_move_line".full_reconcile_id IS NULL '
#
#         # Get analytic account filter
#         analytic_account_ids = data['form'].get('analytic_account_ids', [])
#         analytic_clause = ""
#         analytic_params = []
#
#         if analytic_account_ids:
#             # We'll filter by analytic_distribution in Python since it's a JSON field
#             analytic_clause = ' AND "account_move_line".analytic_distribution IS NOT NULL '
#
#         params = [partner.id, tuple(data['computed']['move_state']),
#                   tuple(data['computed']['account_ids'])] + query_get_data[2]
#
#         query = """
#             SELECT "account_move_line".id, "account_move_line".date, j.code, acc.code as a_code, acc.name as a_name,
#                    "account_move_line".ref, m.name as move_name, "account_move_line".name,
#                    "account_move_line".debit, "account_move_line".credit, "account_move_line".amount_currency,
#                    "account_move_line".currency_id, c.symbol AS currency_code,
#                    "account_move_line".analytic_distribution
#             FROM """ + query_get_data[0] + """
#             LEFT JOIN account_journal j ON ("account_move_line".journal_id = j.id)
#             LEFT JOIN account_account acc ON ("account_move_line".account_id = acc.id)
#             LEFT JOIN res_currency c ON ("account_move_line".currency_id=c.id)
#             LEFT JOIN account_move m ON (m.id="account_move_line".move_id)
#             WHERE "account_move_line".partner_id = %s
#                 AND m.state IN %s
#                 AND "account_move_line".account_id IN %s AND """ + query_get_data[
#             1] + reconcile_clause + analytic_clause + """
#             ORDER BY "account_move_line".date
#         """
#
#         self.env.cr.execute(query, tuple(params))
#         res = self.env.cr.dictfetchall()
#
#         # Filter by analytic accounts if specified
#         if analytic_account_ids:
#             filtered_res = []
#             for line in res:
#                 if line.get('analytic_distribution'):
#                     import json
#                     try:
#                         distribution = json.loads(line['analytic_distribution']) if isinstance(
#                             line['analytic_distribution'], str) else line['analytic_distribution']
#                         line_analytic_ids = [int(k) for k in distribution.keys()]
#                         if any(analytic_id in line_analytic_ids for analytic_id in analytic_account_ids):
#                             filtered_res.append(line)
#                     except:
#                         pass
#             res = filtered_res
#
#         sum_debit = sum_credit = 0.0
#         lang_code = self.env.context.get('lang') or 'en_US'
#         lang = self.env['res.lang']
#         lang_id = lang._lang_get(lang_code)
#         date_format = lang_id.date_format
#
#         for r in res:
#             sum_debit += r['debit']
#             sum_credit += r['credit']
#             r['progress'] = sum_debit - sum_credit
#             r['displayed_name'] = '-'.join(
#                 r[field_name] for field_name in ('move_name', 'ref', 'name')
#                 if r[field_name] not in (None, '', '/')
#             )
#             r['a_code_name'] = r['a_code'] + ' - ' + r['a_name']
#             full_account.append(r)
#
#         return full_account
#
#     def _sum_partner(self, data, partner, field):
#         """
#         Override the _sum_partner method to filter by analytic accounts
#         """
#         if field not in ['debit', 'credit', 'debit - credit']:
#             return
#
#         # Get analytic account filter
#         analytic_account_ids = data['form'].get('analytic_account_ids', [])
#         analytic_clause = ""
#
#         if analytic_account_ids:
#             analytic_clause = ' AND "account_move_line".analytic_distribution IS NOT NULL '
#
#         query_get_data = self.env['account.move.line'].with_context(
#             data['form'].get('used_context', {})
#         )._query_get()
#         reconcile_clause = "" if data['form']['reconciled'] else ' AND "account_move_line".full_reconcile_id IS NULL '
#
#         params = [partner.id, tuple(data['computed']['move_state']),
#                   tuple(data['computed']['account_ids'])] + query_get_data[2]
#
#         query = """SELECT sum(debit), sum(credit)
#                 FROM """ + query_get_data[0] + """, account_move AS m
#                 WHERE "account_move_line".partner_id = %s
#                     AND m.id = "account_move_line".move_id
#                     AND m.state IN %s
#                     AND account_id IN %s
#                     AND """ + query_get_data[1] + reconcile_clause + analytic_clause
#
#         self.env.cr.execute(query, tuple(params))
#         res = self.env.cr.fetchone()
#
#         # If analytic filter is applied, we need to filter the results
#         if analytic_account_ids:
#             query_lines = """SELECT id, analytic_distribution, debit, credit
#                     FROM """ + query_get_data[0] + """, account_move AS m
#                     WHERE "account_move_line".partner_id = %s
#                         AND m.id = "account_move_line".move_id
#                         AND m.state IN %s
#                         AND account_id IN %s
#                         AND """ + query_get_data[1] + reconcile_clause + analytic_clause
#
#             self.env.cr.execute(query_lines, tuple(params))
#             lines = self.env.cr.dictfetchall()
#
#             total_debit = total_credit = 0.0
#             for line in lines:
#                 if line.get('analytic_distribution'):
#                     import json
#                     try:
#                         distribution = json.loads(line['analytic_distribution']) if isinstance(
#                             line['analytic_distribution'], str) else line['analytic_distribution']
#                         line_analytic_ids = [int(k) for k in distribution.keys()]
#                         if any(analytic_id in line_analytic_ids for analytic_id in analytic_account_ids):
#                             total_debit += line['debit']
#                             total_credit += line['credit']
#                     except:
#                         pass
#             res = (total_debit, total_credit)
#
#         debit = res[0] if res and res[0] else 0.0
#         credit = res[1] if res and res[1] else 0.0
#
#         if field == 'debit':
#             return debit
#         elif field == 'credit':
#             return credit
#         else:
#             return debit - credit
#
#     def _get_partner_type_info(self, data, docs):
#         """
#         Determine what type of partners are in the report
#         Returns dict with display information
#         """
#         if not docs:
#             return {
#                 'has_customers': False,
#                 'has_vendors': False,
#                 'display_label': 'Partners',
#                 'count': 0
#             }
#
#         # Get account IDs from the data
#         account_ids = data.get('computed', {}).get('account_ids', [])
#
#         if not account_ids:
#             return {
#                 'has_customers': False,
#                 'has_vendors': False,
#                 'display_label': 'Partners',
#                 'count': len(docs)
#             }
#
#         # Get the accounts
#         accounts = self.env['account.account'].browse(account_ids)
#
#         # Check account types
#         has_receivable = any(acc.account_type == 'asset_receivable' for acc in accounts)
#         has_payable = any(acc.account_type == 'liability_payable' for acc in accounts)
#
#         # Determine display label
#         if has_receivable and has_payable:
#             display_label = 'Customers & Vendors'
#         elif has_receivable:
#             display_label = 'Customers'
#         elif has_payable:
#             display_label = 'Vendors'
#         else:
#             display_label = 'Partners'
#
#         return {
#             'has_customers': has_receivable,
#             'has_vendors': has_payable,
#             'display_label': display_label,
#             'count': len(docs)
#         }
#
#     def _get_partner_label(self, data, partner):
#         """
#         Get the appropriate label for a specific partner (Customer/Vendor)
#         """
#         # Get account IDs from the data
#         account_ids = data.get('computed', {}).get('account_ids', [])
#
#         if not account_ids:
#             return 'Partner'
#
#         # Get move lines for this partner within the selected accounts
#         move_lines = self.env['account.move.line'].search([
#             ('partner_id', '=', partner.id),
#             ('account_id', 'in', account_ids)
#         ], limit=1)
#
#         if move_lines:
#             account_type = move_lines.account_id.account_type
#             if account_type == 'asset_receivable':
#                 return 'Customer'
#             elif account_type == 'liability_payable':
#                 return 'Vendor'
#
#         return 'Partner'
#
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         """
#         Override the main report method to add custom values
#         """
#         # Get parent report values
#         res = super()._get_report_values(docids, data)
#
#         # Get partner type information
#         partner_type_info = self._get_partner_type_info(data, res.get('docs', []))
#
#         # Get analytic account names if filtered
#         analytic_names = []
#         if data and data.get('form', {}).get('analytic_account_ids'):
#             analytic_ids = data['form']['analytic_account_ids']
#             analytic_accounts = self.env['account.analytic.account'].browse(analytic_ids)
#             analytic_names = analytic_accounts.mapped('name')
#
#         # Add custom values to the report context
#         res.update({
#             'custom_title': 'Customized Partner Ledger',
#             'report_date': fields.Date.today(),
#             'partner_type_info': partner_type_info,
#             'get_partner_label': self._get_partner_label,
#             'analytic_account_names': analytic_names,
#         })
#
#         return res
#
#     def _get_partner_opening_balance(self, data, partner):
#         """
#         Calculate opening balance for a partner
#         """
#         # Get analytic account filter
#         analytic_account_ids = data['form'].get('analytic_account_ids', [])
#         analytic_clause = ""
#
#         if analytic_account_ids:
#             analytic_clause = ' AND "account_move_line".analytic_distribution IS NOT NULL '
#
#         query_get_data = self.env['account.move.line'].with_context(
#             data['form'].get('used_context', {})
#         )._query_get()
#
#         reconcile_clause = "" if data['form']['reconciled'] else \
#             ' AND "account_move_line".full_reconcile_id IS NULL '
#
#         date_from = data['form'].get('date_from')
#         date_clause = ""
#         params = [partner.id, tuple(data['computed']['move_state']),
#                   tuple(data['computed']['account_ids'])]
#
#         if date_from:
#             date_clause = ' AND "account_move_line".date < %s '
#             params.append(date_from)
#
#         params.extend(query_get_data[2])
#
#         query = """
#             SELECT
#                 "account_move_line".id,
#                 "account_move_line".analytic_distribution,
#                 COALESCE(SUM(debit), 0.0) as total_debit,
#                 COALESCE(SUM(credit), 0.0) as total_credit
#             FROM """ + query_get_data[0] + """, account_move AS m
#             WHERE "account_move_line".partner_id = %s
#                 AND m.id = "account_move_line".move_id
#                 AND m.state IN %s
#                 AND account_id IN %s
#                 """ + date_clause + """
#                 AND """ + query_get_data[1] + reconcile_clause + analytic_clause + """
#             GROUP BY "account_move_line".id
#         """
#
#         self.env.cr.execute(query, tuple(params))
#         results = self.env.cr.dictfetchall()
#
#         # Filter by analytic accounts if specified
#         total_debit = total_credit = 0.0
#         if analytic_account_ids and results:
#             for line in results:
#                 if line.get('analytic_distribution'):
#                     import json
#                     try:
#                         distribution = json.loads(line['analytic_distribution']) if isinstance(
#                             line['analytic_distribution'], str) else line['analytic_distribution']
#                         line_analytic_ids = [int(k) for k in distribution.keys()]
#                         if any(analytic_id in line_analytic_ids for analytic_id in analytic_account_ids):
#                             total_debit += line['total_debit']
#                             total_credit += line['total_credit']
#                     except:
#                         pass
#         else:
#             for line in results:
#                 total_debit += line['total_debit']
#                 total_credit += line['total_credit']
#
#         return total_debit - total_credit


# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
import time
from odoo import api, models, fields, _
from odoo.exceptions import UserError


class ReportPartnerLedgerCustom(models.AbstractModel):
    _inherit = 'report.accounting_pdf_reports.report_partnerledger'
    _description = 'Custom Partner Ledger Report'

    def _lines(self, data, partner):
        """
        Override the _lines method to filter by analytic accounts
        """
        full_account = []
        currency = self.env['res.currency']
        query_get_data = self.env['account.move.line'].with_context(
            data['form'].get('used_context', {})
        )._query_get()

        # SAFE: Use .get() with default False
        reconcile_clause = "" if data['form'].get('reconciled',
                                                  False) else ' AND "account_move_line".full_reconcile_id IS NULL '

        analytic_account_ids = data['form'].get('analytic_account_ids', [])
        analytic_clause = ""

        if analytic_account_ids:
            analytic_clause = ' AND "account_move_line".analytic_distribution IS NOT NULL '

        params = [partner.id, tuple(data['computed']['move_state']),
                  tuple(data['computed']['account_ids'])] + query_get_data[2]

        query = """
            SELECT "account_move_line".id, "account_move_line".date, j.code, COALESCE(acc.code, '') as a_code, acc.name as a_name, 
                   "account_move_line".ref, m.name as move_name, "account_move_line".name, 
                   "account_move_line".debit, "account_move_line".credit, "account_move_line".amount_currency,
                   "account_move_line".currency_id, c.symbol AS currency_code,
                   "account_move_line".analytic_distribution
            FROM """ + query_get_data[0] + """
            LEFT JOIN account_journal j ON ("account_move_line".journal_id = j.id)
            LEFT JOIN account_account acc ON ("account_move_line".account_id = acc.id)
            LEFT JOIN res_currency c ON ("account_move_line".currency_id=c.id)
            LEFT JOIN account_move m ON (m.id="account_move_line".move_id)
            WHERE "account_move_line".partner_id = %s
                AND m.state IN %s
                AND "account_move_line".account_id IN %s AND """ + query_get_data[
            1] + reconcile_clause + analytic_clause + """
            ORDER BY "account_move_line".date
        """

        self.env.cr.execute(query, tuple(params))
        res = self.env.cr.dictfetchall()

        if analytic_account_ids:
            filtered_res = []
            for line in res:
                if line.get('analytic_distribution'):
                    import json
                    try:
                        distribution = json.loads(line['analytic_distribution']) if isinstance(
                            line['analytic_distribution'], str) else line['analytic_distribution']
                        line_analytic_ids = [int(k) for k in distribution.keys()]
                        if any(analytic_id in line_analytic_ids for analytic_id in analytic_account_ids):
                            filtered_res.append(line)
                    except:
                        pass
            res = filtered_res

        sum_debit = sum_credit = 0.0
        lang_code = self.env.context.get('lang') or 'en_US'
        lang = self.env['res.lang']
        lang_id = lang._lang_get(lang_code)
        date_format = lang_id.date_format

        for r in res:
            sum_debit += r['debit']
            sum_credit += r['credit']
            r['progress'] = sum_debit - sum_credit
            r['displayed_name'] = '-'.join(
                r[field_name] for field_name in ('move_name', 'ref', 'name')
                if r[field_name] not in (None, '', '/')
            )
            a_code = r.get('a_code', '')
            a_name = r.get('a_name', '')
            r['a_code_name'] = (a_code + ' - ' + a_name if a_code else a_name)
            full_account.append(r)

        return full_account

    def _sum_partner(self, data, partner, field):
        """
        Override the _sum_partner method to filter by analytic accounts
        """
        if field not in ['debit', 'credit', 'debit - credit']:
            return

        analytic_account_ids = data['form'].get('analytic_account_ids', [])
        analytic_clause = ""

        if analytic_account_ids:
            analytic_clause = ' AND "account_move_line".analytic_distribution IS NOT NULL '

        query_get_data = self.env['account.move.line'].with_context(
            data['form'].get('used_context', {})
        )._query_get()

        # SAFE: Use .get() with default False
        reconcile_clause = "" if data['form'].get('reconciled',
                                                  False) else ' AND "account_move_line".full_reconcile_id IS NULL '

        params = [partner.id, tuple(data['computed']['move_state']),
                  tuple(data['computed']['account_ids'])] + query_get_data[2]

        query = """SELECT sum(debit), sum(credit)
                FROM """ + query_get_data[0] + """, account_move AS m
                WHERE "account_move_line".partner_id = %s
                    AND m.id = "account_move_line".move_id
                    AND m.state IN %s
                    AND account_id IN %s
                    AND """ + query_get_data[1] + reconcile_clause + analytic_clause

        self.env.cr.execute(query, tuple(params))
        res = self.env.cr.fetchone()

        if analytic_account_ids:
            query_lines = """SELECT id, analytic_distribution, debit, credit
                    FROM """ + query_get_data[0] + """, account_move AS m
                    WHERE "account_move_line".partner_id = %s
                        AND m.id = "account_move_line".move_id
                        AND m.state IN %s
                        AND account_id IN %s
                        AND """ + query_get_data[1] + reconcile_clause + analytic_clause

            self.env.cr.execute(query_lines, tuple(params))
            lines = self.env.cr.dictfetchall()

            total_debit = total_credit = 0.0
            for line in lines:
                if line.get('analytic_distribution'):
                    import json
                    try:
                        distribution = json.loads(line['analytic_distribution']) if isinstance(
                            line['analytic_distribution'], str) else line['analytic_distribution']
                        line_analytic_ids = [int(k) for k in distribution.keys()]
                        if any(analytic_id in line_analytic_ids for analytic_id in analytic_account_ids):
                            total_debit += line['debit']
                            total_credit += line['credit']
                    except:
                        pass
            res = (total_debit, total_credit)

        debit = res[0] if res and res[0] else 0.0
        credit = res[1] if res and res[1] else 0.0

        if field == 'debit':
            return debit
        elif field == 'credit':
            return credit
        else:
            return debit - credit

    def _get_partner_type_info(self, data, docs):
        """
        Determine what type of partners are in the report
        """
        if not docs:
            return {
                'has_customers': False,
                'has_vendors': False,
                'display_label': 'Partners',
                'count': 0
            }

        account_ids = data.get('computed', {}).get('account_ids', [])

        if not account_ids:
            return {
                'has_customers': False,
                'has_vendors': False,
                'display_label': 'Partners',
                'count': len(docs)
            }

        accounts = self.env['account.account'].browse(account_ids)

        has_receivable = any(acc.account_type == 'asset_receivable' for acc in accounts)
        has_payable = any(acc.account_type == 'liability_payable' for acc in accounts)

        if has_receivable and has_payable:
            display_label = 'Customers & Vendors'
        elif has_receivable:
            display_label = 'Customers'
        elif has_payable:
            display_label = 'Vendors'
        else:
            display_label = 'Partners'

        return {
            'has_customers': has_receivable,
            'has_vendors': has_payable,
            'display_label': display_label,
            'count': len(docs)
        }

    def _get_partner_label(self, data, partner):
        """
        Get the appropriate label for a specific partner (Customer/Vendor)
        """
        account_ids = data.get('computed', {}).get('account_ids', [])

        if not account_ids:
            return 'Partner'

        move_lines = self.env['account.move.line'].search([
            ('partner_id', '=', partner.id),
            ('account_id', 'in', account_ids)
        ], limit=1)

        if move_lines:
            account_type = move_lines.account_id.account_type
            if account_type == 'asset_receivable':
                return 'Customer'
            elif account_type == 'liability_payable':
                return 'Vendor'

        return 'Partner'

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Override the main report method to add custom values
        """
        # Initialize missing form fields BEFORE calling parent
        if data and data.get('form'):
            form = data['form']
            if 'reconciled' not in form:
                form['reconciled'] = False
            if 'amount_currency' not in form:
                form['amount_currency'] = False
            if 'partner_ids' not in form:
                form['partner_ids'] = []
            if 'used_context' not in form:
                form['used_context'] = {}
            if 'target_move' not in form:
                form['target_move'] = 'all'
            if 'result_selection' not in form:
                form['result_selection'] = 'customer'

        res = super()._get_report_values(docids, data)

        # ENSURE partner_type_info is always present
        if 'partner_type_info' not in res:
            res['partner_type_info'] = self._get_partner_type_info(data, res.get('docs', []))

        analytic_names = []
        if data and data.get('form', {}).get('analytic_account_ids'):
            analytic_ids = data['form']['analytic_account_ids']
            analytic_accounts = self.env['account.analytic.account'].browse(analytic_ids)
            analytic_names = analytic_accounts.mapped('name')

        res.update({
            'custom_title': 'Customized Partner Ledger',
            'report_date': fields.Date.today(),
            'partner_type_info': res.get('partner_type_info', self._get_partner_type_info(data, res.get('docs', []))),
            'get_partner_label': self._get_partner_label,
            'analytic_account_names': analytic_names,
        })

        return res

    def _get_partner_opening_balance(self, data, partner):
        """
        Calculate opening balance for a partner
        """
        analytic_account_ids = data['form'].get('analytic_account_ids', [])
        analytic_clause = ""

        if analytic_account_ids:
            analytic_clause = ' AND "account_move_line".analytic_distribution IS NOT NULL '

        query_get_data = self.env['account.move.line'].with_context(
            data['form'].get('used_context', {})
        )._query_get()

        # SAFE: Use .get() with default False
        reconcile_clause = "" if data['form'].get('reconciled', False) else \
            ' AND "account_move_line".full_reconcile_id IS NULL '

        date_from = data['form'].get('date_from')
        date_clause = ""
        params = [partner.id, tuple(data['computed']['move_state']),
                  tuple(data['computed']['account_ids'])]

        if date_from:
            date_clause = ' AND "account_move_line".date < %s '
            params.append(date_from)

        params.extend(query_get_data[2])

        query = """
            SELECT
                "account_move_line".id,
                "account_move_line".analytic_distribution,
                COALESCE(SUM(debit), 0.0) as total_debit,
                COALESCE(SUM(credit), 0.0) as total_credit
            FROM """ + query_get_data[0] + """, account_move AS m
            WHERE "account_move_line".partner_id = %s
                AND m.id = "account_move_line".move_id
                AND m.state IN %s
                AND account_id IN %s
                """ + date_clause + """
                AND """ + query_get_data[1] + reconcile_clause + analytic_clause + """
            GROUP BY "account_move_line".id
        """

        self.env.cr.execute(query, tuple(params))
        results = self.env.cr.dictfetchall()

        total_debit = total_credit = 0.0
        if analytic_account_ids and results:
            for line in results:
                if line.get('analytic_distribution'):
                    import json
                    try:
                        distribution = json.loads(line['analytic_distribution']) if isinstance(
                            line['analytic_distribution'], str) else line['analytic_distribution']
                        line_analytic_ids = [int(k) for k in distribution.keys()]
                        if any(analytic_id in line_analytic_ids for analytic_id in analytic_account_ids):
                            total_debit += line['total_debit']
                            total_credit += line['total_credit']
                    except:
                        pass
        else:
            for line in results:
                total_debit += line['total_debit']
                total_credit += line['total_credit']

        return total_debit - total_credit