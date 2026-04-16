# -*- coding: utf-8 -*-
import time
from odoo import api, models, fields, _
# -*- coding: utf-8 -*-
import time
from odoo import api, models, fields, _
from odoo.exceptions import UserError


class ReportPartnerLedgerCustom(models.AbstractModel):
    _inherit = 'report.accounting_pdf_reports.report_partnerledger'
    _description = 'Custom Partner Ledger Report'

    def _lines(self, data, partner):
        full_account = []
        company_currency = self.env.company.currency_id

        query_get_data = self.env['account.move.line'].with_context(
            data['form'].get('used_context', {})
        )._query_get()

        reconcile_clause = "" if data['form']['reconciled'] else \
            ' AND "account_move_line".full_reconcile_id IS NULL '

        params = [partner.id, tuple(data['computed']['move_state']),
                  tuple(data['computed']['account_ids'])] + query_get_data[2]

        lang = self.env.context.get('lang') or 'en_US'

        query = """
            SELECT "account_move_line".id, "account_move_line".date, j.code,
                   COALESCE(acc.name->>%s, acc.name->>'en_US', acc.name::text) as a_name,
                   "account_move_line".ref, m.name as move_name,
                   "account_move_line".name, "account_move_line".debit,
                   "account_move_line".credit, "account_move_line".amount_currency,
                   "account_move_line".currency_id, c.symbol AS currency_code,
                   m.invoice_date_due, m.client_order_ref as po_number,
                   p.manual_currency_exchange_rate,
                   lc.name as line_currency_name
            FROM """ + query_get_data[0] + """
            LEFT JOIN account_journal j ON ("account_move_line".journal_id = j.id)
            LEFT JOIN account_account acc ON ("account_move_line".account_id = acc.id)
            LEFT JOIN res_currency c ON ("account_move_line".currency_id = c.id)
            LEFT JOIN res_currency lc ON ("account_move_line".currency_id = lc.id)
            LEFT JOIN account_move m ON (m.id = "account_move_line".move_id)
            LEFT JOIN account_payment p ON (p.move_id = m.id)
            WHERE "account_move_line".partner_id = %s
                AND m.state IN %s
                AND "account_move_line".account_id IN %s AND """ + query_get_data[1] + reconcile_clause + """
            ORDER BY "account_move_line".date
        """

        params_with_lang = [lang] + params
        self.env.cr.execute(query, tuple(params_with_lang))
        res = self.env.cr.dictfetchall()

        sum_debit = 0.0
        sum_credit = 0.0

        for r in res:
            amt_currency = r.get('amount_currency') or 0.0
            has_foreign = (
                r.get('currency_id')
                and r.get('currency_code')
                and amt_currency
            )

            if has_foreign:
                # Show the raw foreign currency amount instead of converting to company currency.
                raw = abs(amt_currency)
                r['debit'] = raw if amt_currency > 0 else 0.0
                r['credit'] = raw if amt_currency < 0 else 0.0
                sum_debit += r['debit']
                sum_credit += r['credit']
                r['progress'] = sum_debit - sum_credit
                # Mark that this line uses a foreign currency for the template
                r['is_foreign_currency'] = True
                r['display_currency_symbol'] = r.get('currency_code') or ''
            else:
                r['is_foreign_currency'] = False
                r['display_currency_symbol'] = company_currency.symbol or ''
                sum_debit += r['debit']
                sum_credit += r['credit']
                r['progress'] = sum_debit - sum_credit

            r['displayed_name'] = r['move_name'] if r['move_name'] else ''
            if r['ref']:
                r['displayed_name'] = r['ref'] if not r['displayed_name'] \
                    else r['displayed_name'] + ' ' + r['ref']
            if r['name'] and r['name'] != '/':
                r['displayed_name'] = r['name'] if not r['displayed_name'] \
                    else r['displayed_name'] + ' ' + r['name']

            r['invoice_date_due'] = r['invoice_date_due'] if r['invoice_date_due'] else ''
            r['po_number'] = r['po_number'] if r['po_number'] else ''

            if data['form']['amount_currency'] and r['currency_id']:
                r['currency_id'] = self.env['res.currency'].browse(r['currency_id'])

            full_account.append(r)

        return full_account

    def _get_partner_summary(self, data, partner):
        """
        Returns a dict with debit/credit/balance totals for the partner summary row.
        If ALL lines for this partner use the same foreign currency, returns totals
        in that foreign currency (so the summary matches the transaction lines).
        Otherwise falls back to company currency via sum_partner().
        """
        lines = self._lines(data, partner)
        company_currency = self.env.company.currency_id

        if not lines:
            return {
                'debit': 0.0,
                'credit': 0.0,
                'balance': 0.0,
                'currency_symbol': company_currency.symbol or '',
                'is_foreign': False,
            }

        # Check if every line is the same foreign currency
        foreign_symbols = set()
        for line in lines:
            if line.get('is_foreign_currency'):
                foreign_symbols.add(line.get('display_currency_symbol', ''))
            else:
                # Mixed or company-currency line present — fall back to company currency
                foreign_symbols = set()
                break

        if len(foreign_symbols) == 1:
            # All lines are in the same foreign currency — sum them in that currency
            symbol = foreign_symbols.pop()
            total_debit = sum(l['debit'] for l in lines)
            total_credit = sum(l['credit'] for l in lines)
            return {
                'debit': total_debit,
                'credit': total_credit,
                'balance': total_debit - total_credit,
                'currency_symbol': symbol,
                'is_foreign': True,
            }
        else:
            # Mixed currencies or company currency — use standard sum_partner (company currency)
            return {
                'debit': self._sum_partner(data, partner, 'debit'),
                'credit': self._sum_partner(data, partner, 'credit'),
                'balance': self._sum_partner(data, partner, 'debit - credit'),
                'currency_symbol': company_currency.symbol or '',
                'is_foreign': False,
            }

    def _sum_partner(self, data, partner, field):
        return super()._sum_partner(data, partner, field)

    def _get_partner_type_info(self, data, docs):
        if not docs:
            return {
                'has_customers': False, 'has_vendors': False,
                'display_label': 'Partners', 'report_title': 'Partner Ledger Report', 'count': 0
            }
        account_ids = data.get('computed', {}).get('account_ids', [])
        if not account_ids:
            return {
                'has_customers': False, 'has_vendors': False,
                'display_label': 'Partners', 'report_title': 'Partner Ledger Report', 'count': len(docs)
            }
        accounts = self.env['account.account'].browse(account_ids)
        has_receivable = any(acc.account_type == 'asset_receivable' for acc in accounts)
        has_payable = any(acc.account_type == 'liability_payable' for acc in accounts)
        if has_receivable and has_payable:
            display_label, report_title = 'Customers & Vendors', 'Customer/Vendor Statement of Report'
        elif has_receivable:
            display_label, report_title = 'Customers', 'Customer Statement of Report'
        elif has_payable:
            display_label, report_title = 'Vendors', 'Vendor Statement of Report'
        else:
            display_label, report_title = 'Partners', 'Partner Ledger Report'
        return {
            'has_customers': has_receivable, 'has_vendors': has_payable,
            'display_label': display_label, 'report_title': report_title, 'count': len(docs)
        }

    def _get_partner_label(self, data, partner):
        account_ids = data.get('computed', {}).get('account_ids', [])
        if not account_ids:
            return 'Partner'
        move_lines = self.env['account.move.line'].search([
            ('partner_id', '=', partner.id),
            ('account_id', 'in', account_ids)
        ], limit=1)
        if move_lines:
            if move_lines.account_id.account_type == 'asset_receivable':
                return 'Customer'
            elif move_lines.account_id.account_type == 'liability_payable':
                return 'Vendor'
        return 'Partner'

    @api.model
    def _get_report_values(self, docids, data=None):
        res = super()._get_report_values(docids, data)
        partner_type_info = self._get_partner_type_info(data, res.get('docs', []))
        res.update({
            'custom_title': 'Customized Partner Ledger',
            'report_date': fields.Date.today(),
            'partner_type_info': partner_type_info,
            'get_partner_label': self._get_partner_label,
            'get_partner_summary': self._get_partner_summary,  # NEW: expose to template
        })
        return res

    def _get_partner_opening_balance(self, data, partner):
        query_get_data = self.env['account.move.line'].with_context(
            data['form'].get('used_context', {})
        )._query_get()
        reconcile_clause = "" if data['form']['reconciled'] else \
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
            SELECT COALESCE(SUM(debit), 0.0) as total_debit,
                   COALESCE(SUM(credit), 0.0) as total_credit
            FROM """ + query_get_data[0] + """, account_move AS m
            WHERE "account_move_line".partner_id = %s
                AND m.id = "account_move_line".move_id
                AND m.state IN %s
                AND account_id IN %s
                """ + date_clause + """
                AND """ + query_get_data[1] + reconcile_clause
        self.env.cr.execute(query, tuple(params))
        result = self.env.cr.fetchone()
        return (result[0] - result[1]) if result else 0.0










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
#         full_account = []
#         company_currency = self.env.company.currency_id
#
#         query_get_data = self.env['account.move.line'].with_context(
#             data['form'].get('used_context', {})
#         )._query_get()
#
#         reconcile_clause = "" if data['form']['reconciled'] else \
#             ' AND "account_move_line".full_reconcile_id IS NULL '
#
#         params = [partner.id, tuple(data['computed']['move_state']),
#                   tuple(data['computed']['account_ids'])] + query_get_data[2]
#
#         lang = self.env.context.get('lang') or 'en_US'
#
#         query = """
#             SELECT "account_move_line".id, "account_move_line".date, j.code,
#                    COALESCE(acc.name->>%s, acc.name->>'en_US', acc.name::text) as a_name,
#                    "account_move_line".ref, m.name as move_name,
#                    "account_move_line".name, "account_move_line".debit,
#                    "account_move_line".credit, "account_move_line".amount_currency,
#                    "account_move_line".currency_id, c.symbol AS currency_code,
#                    m.invoice_date_due, m.client_order_ref as po_number,
#                    p.manual_currency_exchange_rate,
#                    lc.name as line_currency_name
#             FROM """ + query_get_data[0] + """
#             LEFT JOIN account_journal j ON ("account_move_line".journal_id = j.id)
#             LEFT JOIN account_account acc ON ("account_move_line".account_id = acc.id)
#             LEFT JOIN res_currency c ON ("account_move_line".currency_id = c.id)
#             LEFT JOIN res_currency lc ON ("account_move_line".currency_id = lc.id)
#             LEFT JOIN account_move m ON (m.id = "account_move_line".move_id)
#             LEFT JOIN account_payment p ON (p.move_id = m.id)
#             WHERE "account_move_line".partner_id = %s
#                 AND m.state IN %s
#                 AND "account_move_line".account_id IN %s AND """ + query_get_data[1] + reconcile_clause + """
#             ORDER BY "account_move_line".date
#         """
#
#         params_with_lang = [lang] + params
#         self.env.cr.execute(query, tuple(params_with_lang))
#         res = self.env.cr.dictfetchall()
#
#         sum_debit = 0.0
#         sum_credit = 0.0
#
#         for r in res:
#             manual_rate = r.get('manual_currency_exchange_rate') or 1.0
#             amt_currency = r.get('amount_currency') or 0.0
#             has_foreign = (
#                 r.get('currency_id')
#                 and manual_rate != 1.0
#                 and amt_currency
#             )
#
#             if has_foreign:
#                 # Replace debit/credit with SAR-converted values
#                 raw = abs(amt_currency)
#                 converted = raw * manual_rate
#                 r['debit'] = converted if amt_currency > 0 else 0.0
#                 r['credit'] = converted if amt_currency < 0 else 0.0
#
#             sum_debit += r['debit']
#             sum_credit += r['credit']
#             r['progress'] = sum_debit - sum_credit
#
#             r['displayed_name'] = r['move_name'] if r['move_name'] else ''
#             if r['ref']:
#                 r['displayed_name'] = r['ref'] if not r['displayed_name'] \
#                     else r['displayed_name'] + ' ' + r['ref']
#             if r['name'] and r['name'] != '/':
#                 r['displayed_name'] = r['name'] if not r['displayed_name'] \
#                     else r['displayed_name'] + ' ' + r['name']
#
#             r['invoice_date_due'] = r['invoice_date_due'] if r['invoice_date_due'] else ''
#             r['po_number'] = r['po_number'] if r['po_number'] else ''
#
#             if data['form']['amount_currency'] and r['currency_id']:
#                 r['currency_id'] = self.env['res.currency'].browse(r['currency_id'])
#
#             full_account.append(r)
#
#         return full_account
#
#     def _sum_partner(self, data, partner, field):
#         return super()._sum_partner(data, partner, field)
#
#     def _get_partner_type_info(self, data, docs):
#         if not docs:
#             return {
#                 'has_customers': False, 'has_vendors': False,
#                 'display_label': 'Partners', 'report_title': 'Partner Ledger Report', 'count': 0
#             }
#         account_ids = data.get('computed', {}).get('account_ids', [])
#         if not account_ids:
#             return {
#                 'has_customers': False, 'has_vendors': False,
#                 'display_label': 'Partners', 'report_title': 'Partner Ledger Report', 'count': len(docs)
#             }
#         accounts = self.env['account.account'].browse(account_ids)
#         has_receivable = any(acc.account_type == 'asset_receivable' for acc in accounts)
#         has_payable = any(acc.account_type == 'liability_payable' for acc in accounts)
#         if has_receivable and has_payable:
#             display_label, report_title = 'Customers & Vendors', 'Customer/Vendor Statement of Report'
#         elif has_receivable:
#             display_label, report_title = 'Customers', 'Customer Statement of Report'
#         elif has_payable:
#             display_label, report_title = 'Vendors', 'Vendor Statement of Report'
#         else:
#             display_label, report_title = 'Partners', 'Partner Ledger Report'
#         return {
#             'has_customers': has_receivable, 'has_vendors': has_payable,
#             'display_label': display_label, 'report_title': report_title, 'count': len(docs)
#         }
#
#     def _get_partner_label(self, data, partner):
#         account_ids = data.get('computed', {}).get('account_ids', [])
#         if not account_ids:
#             return 'Partner'
#         move_lines = self.env['account.move.line'].search([
#             ('partner_id', '=', partner.id),
#             ('account_id', 'in', account_ids)
#         ], limit=1)
#         if move_lines:
#             if move_lines.account_id.account_type == 'asset_receivable':
#                 return 'Customer'
#             elif move_lines.account_id.account_type == 'liability_payable':
#                 return 'Vendor'
#         return 'Partner'
#
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         res = super()._get_report_values(docids, data)
#         partner_type_info = self._get_partner_type_info(data, res.get('docs', []))
#         res.update({
#             'custom_title': 'Customized Partner Ledger',
#             'report_date': fields.Date.today(),
#             'partner_type_info': partner_type_info,
#             'get_partner_label': self._get_partner_label,
#         })
#         return res
#
#     def _get_partner_opening_balance(self, data, partner):
#         query_get_data = self.env['account.move.line'].with_context(
#             data['form'].get('used_context', {})
#         )._query_get()
#         reconcile_clause = "" if data['form']['reconciled'] else \
#             ' AND "account_move_line".full_reconcile_id IS NULL '
#         date_from = data['form'].get('date_from')
#         date_clause = ""
#         params = [partner.id, tuple(data['computed']['move_state']),
#                   tuple(data['computed']['account_ids'])]
#         if date_from:
#             date_clause = ' AND "account_move_line".date < %s '
#             params.append(date_from)
#         params.extend(query_get_data[2])
#         query = """
#             SELECT COALESCE(SUM(debit), 0.0) as total_debit,
#                    COALESCE(SUM(credit), 0.0) as total_credit
#             FROM """ + query_get_data[0] + """, account_move AS m
#             WHERE "account_move_line".partner_id = %s
#                 AND m.id = "account_move_line".move_id
#                 AND m.state IN %s
#                 AND account_id IN %s
#                 """ + date_clause + """
#                 AND """ + query_get_data[1] + reconcile_clause
#         self.env.cr.execute(query, tuple(params))
#         result = self.env.cr.fetchone()
#         return (result[0] - result[1]) if result else 0.0
#
