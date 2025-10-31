# -*- coding: utf-8 -*-
from odoo import api, models




class ReportFinancialInherit(models.AbstractModel):
_inherit = 'report.accounting_pdf_reports.report_financial'


def _compute_account_balance(self, accounts):
""" compute the balance, debit and credit for the provided accounts
Apply analytic filter if `analytic_account_ids` is set in context.
"""
mapping = {
'balance': "COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance",
'debit': "COALESCE(SUM(debit), 0) as debit",
'credit': "COALESCE(SUM(credit), 0) as credit",
}


res = {}
for account in accounts:
res[account.id] = dict.fromkeys(mapping, 0.0)
if not accounts:
return res


# Build base query using existing _query_get (it provides domain filters & joins)
tables, where_clause, where_params = self.env['account.move.line']._query_get()
# fallback if tables is None
tables = tables.replace('"', '') if tables else 'account_move_line'


wheres = [""]
if where_clause.strip():
wheres.append(where_clause.strip())
filters = ' AND '.join(wheres)


analytic_account_ids = None
# First, prefer explicit values passed from wizard via data/form -> check context
ctx_analytic = self.env.context.get('analytic_account_ids')
if ctx_analytic:
# ctx may pass list of ids
analytic_account_ids = tuple(ctx_analytic) if isinstance(ctx_analytic, (list, tuple)) else (ctx_analytic,)


# If analytic filter set, add an EXISTS subquery on account_analytic_line
analytic_exists = ''
params = (tuple(accounts._ids),)
if analytic_account_ids:
analytic_exists = ' AND EXISTS (SELECT 1 FROM account_analytic_line aal WHERE aal.move_line_id = account_move_line.id AND aal.account_id IN %s) '
params += (analytic_account_ids,)


# add remaining where params
params += tuple(where_params)


request = (
'SELECT account_id as id, ' + ', '.join(mapping.values()) +
' FROM ' + tables +
' WHERE account_id IN %s ' + filters + analytic_exists +
' GROUP BY account_id'
)


self.env.cr.execute(request, params)
for row in self.env.cr.dictfetchall():
res[row['id']] = row
return res