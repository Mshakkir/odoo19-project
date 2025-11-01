# -*- coding: utf-8 -*-
import time
from odoo import api, models, _
from odoo.exceptions import UserError


class ReportFinancial(models.AbstractModel):
    _name = 'report.accounting_pdf_reports.report_financial'
    _description = 'Financial Reports'

    # -------------------------------------------------------------------------
    # ACCOUNT BALANCE COMPUTATION
    # -------------------------------------------------------------------------
    def _compute_account_balance(self, accounts):
        """Compute balance, debit, and credit for provided accounts."""
        mapping = {
            'balance': "COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0) AS balance",
            'debit': "COALESCE(SUM(debit), 0) AS debit",
            'credit': "COALESCE(SUM(credit), 0) AS credit",
        }

        res = {account.id: dict.fromkeys(mapping, 0.0) for account in accounts}
        if not accounts:
            return res

        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = tables.replace('"', '') if tables else "account_move_line"

        filters = ""
        if where_clause.strip():
            filters = " AND " + where_clause.strip()

        query = f"""
            SELECT account_id AS id, {', '.join(mapping.values())}
            FROM {tables}
            WHERE account_id IN %s {filters}
            GROUP BY account_id
        """

        params = (tuple(accounts.ids),) + tuple(where_params)
        self.env.cr.execute(query, params)
        for row in self.env.cr.dictfetchall():
            res[row['id']] = row
        return res

    # -------------------------------------------------------------------------
    # REPORT BALANCE COMPUTATION
    # -------------------------------------------------------------------------
    def _compute_report_balance(self, reports):
        """
        Compute credit, debit, and balance per financial report line.
        Supports types: accounts, account_type, account_report, and sum.
        """
        res = {}
        fields = ['credit', 'debit', 'balance']

        for report in reports:
            if report.id in res:
                continue

            res[report.id] = {fn: 0.0 for fn in fields}

            if report.type == 'accounts':
                # Sum of linked accounts
                res[report.id]['account'] = self._compute_account_balance(report.account_ids)
                for value in res[report.id]['account'].values():
                    for field in fields:
                        res[report.id][field] += value.get(field, 0.0)

            elif report.type == 'account_type':
                # Sum of accounts by account type
                accounts = self.env['account.account'].search([
                    ('account_type', 'in', report.account_type_ids.mapped('type'))
                ])
                res[report.id]['account'] = self._compute_account_balance(accounts)
                for value in res[report.id]['account'].values():
                    for field in fields:
                        res[report.id][field] += value.get(field, 0.0)

            elif report.type == 'account_report' and report.account_report_id:
                # Linked financial report
                sub_res = self._compute_report_balance(report.account_report_id)
                for value in sub_res.values():
                    for field in fields:
                        res[report.id][field] += value[field]

            elif report.type == 'sum':
                # Sum of children reports
                sub_res = self._compute_report_balance(report.children_ids)
                for value in sub_res.values():
                    for field in fields:
                        res[report.id][field] += value[field]

        return res

    # -------------------------------------------------------------------------
    # LINE GENERATION FOR PDF
    # -------------------------------------------------------------------------
    def get_account_lines(self, data):
        """Generate financial report lines for rendering in PDF."""
        lines = []

        account_report = self.env['account.financial.report'].browse(data['account_report_id'][0])
        child_reports = account_report._get_children_by_order()
        res = self.with_context(data.get('used_context'))._compute_report_balance(child_reports)

        # Comparison (filter enable)
        if data.get('enable_filter'):
            comparison_res = self.with_context(data.get('comparison_context'))._compute_report_balance(child_reports)
            for report_id, value in comparison_res.items():
                res[report_id]['comp_bal'] = value['balance']
                if 'account' in res[report_id]:
                    for acc_id, acc_val in res[report_id]['account'].items():
                        acc_val['comp_bal'] = comparison_res[report_id]['account'].get(acc_id, {}).get('balance', 0.0)

        # Build report + account lines
        for report in child_reports:
            vals = {
                'name': report.name,
                'balance': res[report.id]['balance'] * float(report.sign),
                'type': 'report',
                'level': report.style_overwrite or report.level,
                'account_type': report.type or False,
            }

            if data.get('debit_credit'):
                vals['debit'] = res[report.id]['debit']
                vals['credit'] = res[report.id]['credit']

            if data.get('enable_filter'):
                vals['balance_cmp'] = res[report.id].get('comp_bal', 0.0) * float(report.sign)

            lines.append(vals)

            if report.display_detail == 'no_detail':
                continue

            # Add account-level breakdown
            if res[report.id].get('account'):
                sub_lines = []
                for account_id, value in res[report.id]['account'].items():
                    account = self.env['account.account'].browse(account_id)
                    line_vals = {
                        'name': f"{account.code} {account.name}",
                        'balance': value['balance'] * float(report.sign),
                        'type': 'account',
                        'level': 4 if report.display_detail == 'detail_with_hierarchy' else report.level + 1,
                        'account_type': account.account_type,
                    }

                    show_line = False
                    if data.get('debit_credit'):
                        line_vals['debit'] = value['debit']
                        line_vals['credit'] = value['credit']
                        if not self.env.company.currency_id.is_zero(line_vals['debit']) or not self.env.company.currency_id.is_zero(line_vals['credit']):
                            show_line = True

                    if not self.env.company.currency_id.is_zero(line_vals['balance']):
                        show_line = True

                    if data.get('enable_filter'):
                        line_vals['balance_cmp'] = value.get('comp_bal', 0.0) * float(report.sign)
                        if not self.env.company.currency_id.is_zero(line_vals['balance_cmp']):
                            show_line = True

                    if show_line:
                        sub_lines.append(line_vals)

                lines += sorted(sub_lines, key=lambda l: l['name'])

        return lines

    # -------------------------------------------------------------------------
    # REPORT VALUES FOR QWEB TEMPLATE
    # -------------------------------------------------------------------------
    @api.model
    def _get_report_values(self, docids, data=None):
        if not data or not data.get('form') or not self.env.context.get('active_model') or not self.env.context.get('active_id'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))

        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'get_account_lines': self.get_account_lines(data['form']),
        }










# import time
# from odoo import api, models, _
# from odoo.exceptions import UserError
#
#
# class ReportFinancial(models.AbstractModel):
#     _name = 'report.accounting_pdf_reports.report_financial'
#     _description = 'Financial Reports'
#
#     def _compute_account_balance(self, accounts):
#         """ compute the balance, debit and credit for the provided accounts
#         """
#         mapping = {
#             'balance': "COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance",
#             'debit': "COALESCE(SUM(debit), 0) as debit",
#             'credit': "COALESCE(SUM(credit), 0) as credit",
#         }
#
#         res = {}
#         for account in accounts:
#             res[account.id] = dict.fromkeys(mapping, 0.0)
#         if accounts:
#             tables, where_clause, where_params = self.env['account.move.line']._query_get()
#             tables = tables.replace('"', '') if tables else "account_move_line"
#             wheres = [""]
#             if where_clause.strip():
#                 wheres.append(where_clause.strip())
#             filters = " AND ".join(wheres)
#             request = "SELECT account_id as id, " + ', '.join(mapping.values()) + \
#                        " FROM " + tables + \
#                        " WHERE account_id IN %s " \
#                             + filters + \
#                        " GROUP BY account_id"
#             params = (tuple(accounts._ids),) + tuple(where_params)
#             self.env.cr.execute(request, params)
#             for row in self.env.cr.dictfetchall():
#                 res[row['id']] = row
#         return res
#
#     def _compute_report_balance(self, reports):
#         '''returns a dictionary with key=the ID of a record and value=the credit, debit and balance amount
#            computed for this record. If the record is of type :
#                'accounts' : it's the sum of the linked accounts
#                'account_type' : it's the sum of leaf accoutns with such an account_type
#                'account_report' : it's the amount of the related report
#                'sum' : it's the sum of the children of this record (aka a 'view' record)'''
#         res = {}
#         fields = ['credit', 'debit', 'balance']
#         for report in reports:
#             if report.id in res:
#                 continue
#             res[report.id] = dict((fn, 0.0) for fn in fields)
#             if report.type == 'accounts':
#                 # it's the sum of the linked accounts
#                 res[report.id]['account'] = self._compute_account_balance(report.account_ids)
#                 for value in res[report.id]['account'].values():
#                     for field in fields:
#                         res[report.id][field] += value.get(field)
#             elif report.type == 'account_type':
#                 # it's the sum the leaf accounts with such an account type
#                 accounts = self.env['account.account'].search(
#                     [('account_type', 'in', report.account_type_ids.mapped('type'))])
#
#                 res[report.id]['account'] = self._compute_account_balance(accounts)
#                 for value in res[report.id]['account'].values():
#                     for field in fields:
#                         res[report.id][field] += value.get(field)
#             elif report.type == 'account_report' and report.account_report_id:
#                 # it's the amount of the linked report
#                 res2 = self._compute_report_balance(report.account_report_id)
#                 for key, value in res2.items():
#                     for field in fields:
#                         res[report.id][field] += value[field]
#             elif report.type == 'sum':
#                 # it's the sum of the children of this account.report
#                 res2 = self._compute_report_balance(report.children_ids)
#                 for key, value in res2.items():
#                     for field in fields:
#                         res[report.id][field] += value[field]
#         return res
#
#     def get_account_lines(self, data):
#         lines = []
#         account_report = self.env['account.financial.report'].search(
#             [('id', '=', data['account_report_id'][0])])
#         child_reports = account_report._get_children_by_order()
#         res = self.with_context(data.get('used_context'))._compute_report_balance(child_reports)
#         if data['enable_filter']:
#             comparison_res = self.with_context(
#                 data.get('comparison_context'))._compute_report_balance(
#                 child_reports)
#             for report_id, value in comparison_res.items():
#                 res[report_id]['comp_bal'] = value['balance']
#                 report_acc = res[report_id].get('account')
#                 if report_acc:
#                     for account_id, val in comparison_res[report_id].get('account').items():
#                         report_acc[account_id]['comp_bal'] = val['balance']
#         for report in child_reports:
#             vals = {
#                 'name': report.name,
#                 'balance': res[report.id]['balance'] * float(report.sign),
#                 'type': 'report',
#                 'level': bool(report.style_overwrite) and report.style_overwrite or report.level,
#                 'account_type': report.type or False, #used to underline the financial report balances
#             }
#             if data['debit_credit']:
#                 vals['debit'] = res[report.id]['debit']
#                 vals['credit'] = res[report.id]['credit']
#
#             if data['enable_filter']:
#                 vals['balance_cmp'] = res[report.id]['comp_bal'] * float(report.sign)
#
#             lines.append(vals)
#             if report.display_detail == 'no_detail':
#                 #the rest of the loop is used to display the details of the financial report, so it's not needed here.
#                 continue
#             if res[report.id].get('account'):
#                 sub_lines = []
#                 for account_id, value in res[report.id]['account'].items():
#                     #if there are accounts to display, we add them to the lines with a level equals to their level in
#                     #the COA + 1 (to avoid having them with a too low level that would conflicts with the level of data
#                     #financial reports for Assets, liabilities...)
#                     flag = False
#                     account = self.env['account.account'].browse(account_id)
#                     vals = {
#                         'name': account.code + ' ' + account.name,
#                         'balance': value['balance'] * float(report.sign) or 0.0,
#                         'type': 'account',
#                         'level': report.display_detail == 'detail_with_hierarchy' and 4,
#                         'account_type': account.account_type,
#                     }
#                     if data['debit_credit']:
#                         vals['debit'] = value['debit']
#                         vals['credit'] = value['credit']
#                         if not self.env.company.currency_id.is_zero(vals['debit']) or not self.env.company.currency_id.is_zero(vals['credit']):
#                             flag = True
#                     if not self.env.company.currency_id.is_zero(vals['balance']):
#                         flag = True
#                     if data['enable_filter']:
#                         vals['balance_cmp'] = value['comp_bal'] * float(report.sign)
#                         if not self.env.company.currency_id.is_zero(vals['balance_cmp']):
#                             flag = True
#                     if flag:
#                         sub_lines.append(vals)
#                 lines += sorted(sub_lines, key=lambda sub_line: sub_line['name'])
#         return lines
#
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         if not data.get('form') or not self.env.context.get('active_model') or not self.env.context.get('active_id'):
#             raise UserError(_("Form content is missing, this report cannot be printed."))
#
#         model = self.env.context.get('active_model')
#         docs = self.env[model].browse(self.env.context.get('active_id'))
#         report_lines = self.get_account_lines(data.get('form'))
#         return {
#             'doc_ids': self.ids,
#             'doc_model': model,
#             'data': data['form'],
#             'docs': docs,
#             'time': time,
#             'get_account_lines': report_lines,
#         }
