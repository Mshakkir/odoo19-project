# # -*- coding: utf-8 -*-
# from odoo import api, fields, models, _
# from odoo.tools.misc import format_amount
#
#
# class AccountJournal(models.Model):
#     _inherit = 'account.journal'
#
#     bank_statements_source = fields.Selection(
#         selection_add=[('manual', 'Record Manually')],
#         ondelete={'manual': 'set default'},
#         help="Defines how the bank statements will be registered"
#     )
#
#     def create_bank_statement(self):
#         """Return action to create a bank statement.
#         This button should be called only on journals with type =='bank'"""
#         self.ensure_one()
#         action = self.env.ref('bank_reconciliation.action_bank_statement_wiz').read()[0]
#         action['context'] = {
#             'default_journal_id': self.id,
#         }
#         return action
#
#     def get_journal_dashboard_datas(self):
#         """Override to add bank reconciliation data to dashboard"""
#         res = super(AccountJournal, self).get_journal_dashboard_datas()
#
#         if self.type != 'bank':
#             return res
#
#         account_sum = 0.0
#         bank_balance = 0.0
#         currency = self.currency_id or self.company_id.currency_id
#
#         account_ids = tuple(
#             ac for ac in [self.default_account_id.id] if ac
#         )
#
#         if account_ids:
#             amount_field = 'balance' if (
#                     not self.currency_id or self.currency_id == self.company_id.currency_id
#             ) else 'amount_currency'
#
#             # Get total account balance
#             query = """
#                 SELECT sum(%s)
#                 FROM account_move_line
#                 WHERE account_id in %%s
#                 AND date <= %%s
#                 AND parent_state = 'posted';
#             """ % (amount_field,)
#
#             self.env.cr.execute(query, (account_ids, fields.Date.today(),))
#             query_results = self.env.cr.dictfetchall()
#             if query_results and query_results[0].get('sum') is not None:
#                 account_sum = query_results[0].get('sum')
#
#             # Get reconciled bank balance
#             query = """
#                 SELECT sum(%s)
#                 FROM account_move_line
#                 WHERE account_id in %%s
#                 AND date <= %%s
#                 AND statement_date IS NOT NULL
#                 AND parent_state = 'posted';
#             """ % (amount_field,)
#
#             self.env.cr.execute(query, (account_ids, fields.Date.today(),))
#             query_results = self.env.cr.dictfetchall()
#             if query_results and query_results[0].get('sum') is not None:
#                 bank_balance = query_results[0].get('sum')
#
#         difference = currency.round(account_sum - bank_balance)
#
#         res.update({
#             'last_balance': format_amount(self.env, currency.round(bank_balance), currency),
#             'difference': format_amount(self.env, difference, currency)
#         })
#
#         return res

# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools.misc import format_amount


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    # FIX: Override method instead of selection_add
    def _get_bank_statements_available_sources(self):
        values = super()._get_bank_statements_available_sources()
        if ('manual', _('Record Manually')) not in values:
            values.append(('manual', _('Record Manually')))
        return values

    def create_bank_statement(self):
        self.ensure_one()
        action = self.env.ref('bank_reconciliation.action_bank_statement_wiz').read()[0]
        action['context'] = {'default_journal_id': self.id}
        return action

    def get_journal_dashboard_datas(self):
        res = super(AccountJournal, self).get_journal_dashboard_datas()

        if self.type != 'bank':
            return res

        currency = self.currency_id or self.company_id.currency_id
        account_sum = bank_balance = 0.0

        account_ids = tuple([self.default_account_id.id] if self.default_account_id else [])

        if account_ids:
            amount_field = 'balance' if (
                not self.currency_id or self.currency_id == self.company_id.currency_id
            ) else 'amount_currency'

            query = f"""
                SELECT sum({amount_field}) 
                FROM account_move_line 
                WHERE account_id in %s 
                AND date <= %s
                AND parent_state = 'posted';
            """

            self.env.cr.execute(query, (account_ids, fields.Date.today()))
            result = self.env.cr.fetchone()
            account_sum = result[0] if result and result[0] else 0.0

            query = f"""
                SELECT sum({amount_field}) 
                FROM account_move_line 
                WHERE account_id in %s 
                AND date <= %s 
                AND statement_date IS NOT NULL
                AND parent_state = 'posted';
            """

            self.env.cr.execute(query, (account_ids, fields.Date.today()))
            result = self.env.cr.fetchone()
            bank_balance = result[0] if result and result[0] else 0.0

        difference = currency.round(account_sum - bank_balance)

        res.update({
            'last_balance': format_amount(self.env, currency.round(bank_balance), currency),
            'difference': format_amount(self.env, difference, currency)
        })

        return res
