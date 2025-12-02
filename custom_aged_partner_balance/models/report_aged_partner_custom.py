# import time
# from odoo import api, models, fields, _
# from odoo.exceptions import UserError
# from odoo.tools import float_is_zero
# from datetime import datetime
# from dateutil.relativedelta import relativedelta
#
#
# class ReportAgedPartnerBalanceCustom(models.AbstractModel):
#     """
#     Inherited Aged Partner Balance Report with custom features
#     """
#     _inherit = 'report.accounting_pdf_reports.report_agedpartnerbalance'
#     _description = 'Custom Aged Partner Balance Report'
#
#     def _get_partner_move_lines(self, account_type, partner_ids,
#                                 date_from, target_move, period_length):
#         """
#         Override the parent method to add custom functionality
#         """
#         # Call the parent method to get base data
#         res, total, lines = super(ReportAgedPartnerBalanceCustom, self)._get_partner_move_lines(
#             account_type, partner_ids, date_from, target_move, period_length
#         )
#
#         # CUSTOMIZATION 1: Add additional partner information
#         for partner_data in res:
#             if partner_data.get('partner_id'):
#                 partner = self.env['res.partner'].browse(partner_data['partner_id'])
#                 # Add custom fields
#                 partner_data['email'] = partner.email or ''
#                 partner_data['phone'] = partner.phone or ''
#                 partner_data['vat'] = partner.vat or ''
#                 partner_data['ref'] = partner.ref or ''
#                 partner_data['city'] = partner.city or ''
#                 partner_data['country'] = partner.country_id.name if partner.country_id else ''
#                 partner_data['category_names'] = ', '.join(partner.category_id.mapped('name'))
#
#         return res, total, lines
#
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         """
#         Override to add custom report values and context
#         """
#         # Call parent method
#         result = super(ReportAgedPartnerBalanceCustom, self)._get_report_values(docids, data)
#
#         # Add custom report type identifier
#         result['report_type'] = data.get('result_selection', 'customer') if data else 'customer'
#         result['company_name'] = self.env.company.name
#         result['report_date'] = fields.Date.today()
#         result['user_name'] = self.env.user.name
#
#         # Calculate additional statistics
#         partner_lines = result.get('get_partner_lines', [])
#         total_partners = len(partner_lines)
#         partners_with_overdue = sum(1 for p in partner_lines
#                                     if any(p.get(str(i), 0) != 0 for i in range(5)))
#
#         result['total_partners'] = total_partners
#         result['partners_with_overdue'] = partners_with_overdue
#
#         # Add percentage calculations
#         directions = result.get('get_direction', [])
#         if directions and len(directions) > 5:
#             grand_total = directions[5]
#             if grand_total != 0:
#                 result['percentage_breakdown'] = {
#                     'not_due': (directions[6] / grand_total * 100) if grand_total else 0,
#                     'period_0': (directions[0] / grand_total * 100) if grand_total else 0,
#                     'period_1': (directions[1] / grand_total * 100) if grand_total else 0,
#                     'period_2': (directions[2] / grand_total * 100) if grand_total else 0,
#                     'period_3': (directions[3] / grand_total * 100) if grand_total else 0,
#                     'period_4': (directions[4] / grand_total * 100) if grand_total else 0,
#                 }
#
#         return result
#
#     def action_show_details(self):
#         """
#         Open all move lines filtered by aged report settings.
#         """
#         self.ensure_one()
#
#         # Prepare filter domain
#         domain = [
#             ('journal_id', 'in', self.journal_ids.ids),
#             ('date', '<=', self.date_from),
#         ]
#
#         # Apply partner type
#         if self.result_selection == 'customer':
#             domain += [('account_id.account_type', '=', 'asset_receivable')]
#         elif self.result_selection == 'supplier':
#             domain += [('account_id.account_type', '=', 'liability_payable')]
#
#         # Posted or All
#         if self.target_move == 'posted':
#             domain += [('parent_state', '=', 'posted')]
#
#         action = {
#             'name': "Aged Details",
#             'type': 'ir.actions.act_window',
#             'view_mode': 'tree,form',
#             'res_model': 'account.move.line',
#             'domain': domain,
#             'context': {'search_default_group_by_partner': 1},
#         }
#         return action
#


# wizard/aged_partner.py

import time
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAgedTrialBalance(models.TransientModel):
    _name = 'account.aged.trial.balance'
    _inherit = 'account.common.partner.report'
    _description = 'Account Aged Trial balance Report'

    period_length = fields.Integer(string='Period Length (days)', required=True, default=30)
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True)
    date_from = fields.Date(default=lambda *a: time.strftime('%Y-%m-%d'))

    def _get_report_data(self, data):
        res = {}
        data = self.pre_print_report(data)
        data['form'].update(self.read(['period_length'])[0])
        period_length = data['form']['period_length']

        if period_length <= 0:
            raise UserError(_('You must set a period length greater than 0.'))
        if not data['form']['date_from']:
            raise UserError(_('You must set a start date.'))

        start = data['form']['date_from']

        for i in range(5)[::-1]:
            stop = start - relativedelta(days=period_length - 1)
            res[str(i)] = {
                'name': (i != 0 and (str((5 - (i + 1)) * period_length) + '-' + str((5 - i) * period_length)) or ('+' + str(4 * period_length))),
                'stop': start.strftime('%Y-%m-%d'),
                'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
            }
            start = stop - relativedelta(days=1)

        data['form'].update(res)
        return data

    def _print_report(self, data):
        data = self._get_report_data(data)
        return self.env.ref('accounting_pdf_reports.action_report_aged_partner_balance') \
            .with_context(landscape=True).report_action(self, data=data)

    # ----------------------------------------------------------------------
    # NEW ADDED METHOD: ACTION SHOW DETAILS
    # ----------------------------------------------------------------------
    def action_show_details(self):
        """
        Open detailed move lines based on the wizard filters.
        """
        self.ensure_one()

        domain = [
            ('journal_id', 'in', self.journal_ids.ids),
            ('date', '<=', self.date_from),
        ]

        # Filter by customer/supplier
        if self.result_selection == 'customer':
            domain += [('account_id.account_type', '=', 'asset_receivable')]
        elif self.result_selection == 'supplier':
            domain += [('account_id.account_type', '=', 'liability_payable')]

        # Posted/all entries
        if self.target_move == 'posted':
            domain += [('parent_state', '=', 'posted')]

        return {
            'name': "Aged Report Details",
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move.line',
            'domain': domain,
            'context': {'search_default_group_by_partner': 1},
        }
