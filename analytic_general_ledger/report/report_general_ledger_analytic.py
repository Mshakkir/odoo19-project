# import time
# from odoo import api, models, _
# from odoo.exceptions import UserError
#
#
# class ReportGeneralLedgerAnalytic(models.AbstractModel):
#     _name = 'report.analytic_general_ledger.report_general_ledger_analytic'
#     _description = 'General Ledger Report with Analytic Accounts'
#     _inherit = 'report.accounting_pdf_reports.report_general_ledger'
#
#     def _get_account_move_entry(self, accounts, analytic_account_ids,
#                                 partner_ids, init_balance,
#                                 sortby, display_account):
#         """Extend to include analytic account name"""
#         cr = self.env.cr
#         MoveLine = self.env['account.move.line']
#         move_lines = {x: [] for x in accounts.ids}
#
#         sql_sort = 'l.date, l.move_id'
#         if sortby == 'sort_journal_partner':
#             sql_sort = 'j.code, p.name, l.move_id'
#
#         context = dict(self.env.context)
#         if analytic_account_ids:
#             context['analytic_account_ids'] = analytic_account_ids
#         if partner_ids:
#             context['partner_ids'] = partner_ids
#
#         tables, where_clause, where_params = MoveLine.with_context(context)._query_get()
#         filters = " AND " + where_clause if where_clause else ""
#         filters = filters.replace('account_move_line__move_id', 'm').replace('account_move_line', 'l')
#
#         sql = ('''SELECT l.id AS lid, l.account_id AS account_id,
#             l.date AS ldate, j.code AS lcode, l.currency_id,
#             l.amount_currency, aa.name AS analytic_account_id,
#             l.ref AS lref, l.name AS lname, COALESCE(l.debit,0) AS debit,
#             COALESCE(l.credit,0) AS credit,
#             (l.debit - l.credit) AS balance,
#             m.name AS move_name, c.symbol AS currency_code,
#             p.name AS partner_name
#             FROM account_move_line l
#             JOIN account_move m ON (l.move_id=m.id)
#             LEFT JOIN res_currency c ON (l.currency_id=c.id)
#             LEFT JOIN res_partner p ON (l.partner_id=p.id)
#             JOIN account_journal j ON (l.journal_id=j.id)
#             JOIN account_account acc ON (l.account_id = acc.id)
#             LEFT JOIN account_analytic_account aa ON (l.analytic_account_id = aa.id)
#             WHERE l.account_id IN %s ''' + filters + '''
#             ORDER BY ''' + sql_sort)
#
#         params = (tuple(accounts.ids),) + tuple(where_params)
#         cr.execute(sql, params)
#
#         for row in cr.dictfetchall():
#             move_lines[row.pop('account_id')].append(row)
#
#         account_res = []
#         for account in accounts:
#             res = {'code': account.code, 'name': account.name,
#                    'debit': 0.0, 'credit': 0.0, 'balance': 0.0,
#                    'move_lines': move_lines[account.id]}
#             for line in res['move_lines']:
#                 res['debit'] += line['debit']
#                 res['credit'] += line['credit']
#                 res['balance'] += line['balance']
#             if display_account == 'all' or res['move_lines']:
#                 account_res.append(res)
#         return account_res
#
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         res = super()._get_report_values(docids, data)
#         res['analytic_account_ids'] = self.env['account.analytic.account'].browse(
#             data['form'].get('analytic_account_ids', []))
#         return res
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AccountReportGeneralLedgerAnalytic(models.TransientModel):
    _inherit = "account.report.general.ledger"

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string='Analytic Accounts',
        help='Filter General Ledger entries by analytic accounts.'
    )

    def _print_report(self, data):
        """Override to pass analytic account info to custom report"""
        records, data = self._get_report_data(data)
        analytic_ids = self.read(['analytic_account_ids'])[0].get('analytic_account_ids', [])
        data['form']['analytic_account_ids'] = analytic_ids
        return self.env.ref('accounting_pdf_reports.action_report_general_ledger').with_context(
            landscape=True).report_action(records, data=data)

    def action_show_details(self):
        """Show detailed general ledger entries with related invoices"""
        self.ensure_one()

        # Validate date range
        if self.date_from > self.date_to:
            raise UserError(_('Start Date must be before End Date.'))

        # Build domain for account.move.line
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('parent_state', '=', 'posted'),
        ]

        # Add analytic account filter
        if self.analytic_account_ids:
            domain.append(('analytic_account_id', 'in', self.analytic_account_ids.ids))

        # Add journal filter
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))

        # Add partner filter if exists
        if hasattr(self, 'partner_ids') and self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))

        # Add account filter based on display_account
        if self.display_account == 'movement':
            # Only accounts with movements
            domain.append(('account_id.internal_group', 'not in', ['off_balance']))
        elif self.display_account == 'not_zero':
            # Accounts with balance != 0 (will be filtered in view)
            domain.append(('account_id.internal_group', 'not in', ['off_balance']))

        # Return tree view with detailed information
        return {
            'name': _('General Ledger Details - Analytic'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {
                'search_default_group_by_account': 1,
                'search_default_group_by_analytic': 1,
                'date_from': self.date_from,
                'date_to': self.date_to,
            },
            'target': 'current',
        }