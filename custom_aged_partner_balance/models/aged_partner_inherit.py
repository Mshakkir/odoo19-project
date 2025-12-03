# # models/aged_partner_inherit.py
#
# from odoo import api, fields, models, _
# from dateutil.relativedelta import relativedelta
#
#
# class AccountAgedTrialBalance(models.TransientModel):
#     _inherit = 'account.aged.trial.balance'
#
#     def show_details(self):
#         """
#         Show detailed aged balance breakdown with aging periods.
#         """
#         self.ensure_one()
#
#         # Get the report parser to calculate aging
#         report_lines = self._get_aging_data()
#
#         # Clear existing detail lines
#         self.env['account.aged.detail.line'].search([]).unlink()
#
#         # Create detail lines
#         DetailLine = self.env['account.aged.detail.line']
#         detail_ids = []
#
#         for line_data in report_lines:
#             vals = {
#                 'partner_id': line_data.get('partner_id'),
#                 'partner_name': line_data.get('partner_name'),
#                 'not_due': line_data.get('not_due', 0.0),
#                 'period_0': line_data.get('period_0', 0.0),
#                 'period_1': line_data.get('period_1', 0.0),
#                 'period_2': line_data.get('period_2', 0.0),
#                 'period_3': line_data.get('period_3', 0.0),
#                 'period_4': line_data.get('period_4', 0.0),
#                 'total': line_data.get('total', 0.0),
#                 'wizard_id': self.id,
#             }
#             detail_line = DetailLine.create(vals)
#             detail_ids.append(detail_line.id)
#
#         # Action name based on report type
#         if self.result_selection == 'customer':
#             action_name = _('Aged Receivable Details')
#         elif self.result_selection == 'supplier':
#             action_name = _('Aged Payable Details')
#         else:
#             action_name = _('Aged Partner Balance Details')
#
#         return {
#             'name': action_name,
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.aged.detail.line',
#             'view_mode': 'list,form',
#             'domain': [('id', 'in', detail_ids)],
#             'target': 'current',
#             'context': {'create': False, 'edit': False},
#         }
#
#     def _get_aging_data(self):
#         """
#         Calculate aging breakdown for each partner.
#         """
#         self.ensure_one()
#
#         # Calculate period dates
#         periods = self._calculate_periods()
#
#         # Build domain for move lines
#         domain = [
#             ('account_id.account_type', 'in', self._get_account_types()),
#             ('reconciled', '=', False),
#             ('date', '<=', self.date_from),
#         ]
#
#         if self.journal_ids:
#             domain.append(('journal_id', 'in', self.journal_ids.ids))
#
#         if self.partner_ids:
#             domain.append(('partner_id', 'in', self.partner_ids.ids))
#
#         if self.target_move == 'posted':
#             domain.append(('parent_state', '=', 'posted'))
#
#         # Get all move lines
#         move_lines = self.env['account.move.line'].search(domain)
#
#         # Group by partner and calculate aging
#         partner_data = {}
#         for line in move_lines:
#             partner_id = line.partner_id.id
#             if partner_id not in partner_data:
#                 partner_data[partner_id] = {
#                     'partner_id': partner_id,
#                     'partner_name': line.partner_id.name,
#                     'not_due': 0.0,
#                     'period_0': 0.0,
#                     'period_1': 0.0,
#                     'period_2': 0.0,
#                     'period_3': 0.0,
#                     'period_4': 0.0,
#                     'total': 0.0,
#                 }
#
#             # Calculate amount (debit - credit for receivables, credit - debit for payables)
#             if self.result_selection == 'customer':
#                 amount = line.debit - line.credit
#             else:
#                 amount = line.credit - line.debit
#
#             # Determine which aging bucket
#             date_due = line.date_maturity or line.date
#             period_key = self._get_period_key(date_due, periods)
#
#             partner_data[partner_id][period_key] += amount
#             partner_data[partner_id]['total'] += amount
#
#         return list(partner_data.values())
#
#     def _calculate_periods(self):
#         """
#         Calculate aging period dates.
#         """
#         periods = {}
#         start_date = self.date_from
#
#         for i in range(5):
#             period_key = f'period_{4 - i}'
#             end_date = start_date
#             start_date = end_date - relativedelta(days=self.period_length - 1)
#
#             periods[period_key] = {
#                 'start': start_date,
#                 'end': end_date,
#             }
#
#             start_date = start_date - relativedelta(days=1)
#
#         # Not due (future dates)
#         periods['not_due'] = {
#             'start': self.date_from + relativedelta(days=1),
#             'end': fields.Date.today() + relativedelta(years=10),
#         }
#
#         return periods
#
#     def _get_period_key(self, date_due, periods):
#         """
#         Determine which period a date falls into.
#         """
#         if date_due > self.date_from:
#             return 'not_due'
#
#         for i in range(5):
#             period_key = f'period_{i}'
#             if periods[period_key]['start'] <= date_due <= periods[period_key]['end']:
#                 return period_key
#
#         # Oldest period
#         return 'period_4'
#
#     def _get_account_types(self):
#         """
#         Get account types based on report selection.
#         """
#         if self.result_selection == 'customer':
#             return ['asset_receivable']
#         elif self.result_selection == 'supplier':
#             return ['liability_payable']
#         else:
#             return ['asset_receivable', 'liability_payable']
#
#
# class AccountAgedDetailLine(models.TransientModel):
#     _name = 'account.aged.detail.line'
#     _description = 'Aged Balance Detail Line'
#     _order = 'total desc, partner_name'
#
#     wizard_id = fields.Many2one('account.aged.trial.balance', string='Wizard', ondelete='cascade')
#     partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
#     partner_name = fields.Char(string='Partner Name', readonly=True)
#     trust = fields.Selection(related='partner_id.trust', string='Trust', readonly=True, store=True)
#     email = fields.Char(related='partner_id.email', string='Email', readonly=True)
#     phone = fields.Char(related='partner_id.phone', string='Phone', readonly=True)
#     vat = fields.Char(related='partner_id.vat', string='Tax ID', readonly=True)
#
#     not_due = fields.Monetary(string='Not Due', readonly=True, currency_field='currency_id')
#     period_0 = fields.Monetary(string='0-30', readonly=True, currency_field='currency_id')
#     period_1 = fields.Monetary(string='31-60', readonly=True, currency_field='currency_id')
#     period_2 = fields.Monetary(string='61-90', readonly=True, currency_field='currency_id')
#     period_3 = fields.Monetary(string='91-120', readonly=True, currency_field='currency_id')
#     period_4 = fields.Monetary(string='120+', readonly=True, currency_field='currency_id')
#     total = fields.Monetary(string='Total', readonly=True, currency_field='currency_id')
#
#     currency_id = fields.Many2one('res.currency', string='Currency',
#                                   default=lambda self: self.env.company.currency_id)
#
#     def action_view_journal_entries(self):
#         """
#         View journal entries for this partner.
#         """
#         self.ensure_one()
#         wizard = self.wizard_id
#
#         domain = [
#             ('partner_id', '=', self.partner_id.id),
#             ('account_id.account_type', 'in', wizard._get_account_types()),
#             ('reconciled', '=', False),
#             ('date', '<=', wizard.date_from),
#         ]
#
#         if wizard.journal_ids:
#             domain.append(('journal_id', 'in', wizard.journal_ids.ids))
#
#         if wizard.target_move == 'posted':
#             domain.append(('parent_state', '=', 'posted'))
#
#         return {
#             'name': _('Journal Entries: %s') % self.partner_name,
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.move.line',
#             'view_mode': 'list,form',
#             'domain': domain,
#             'target': 'current',
#         }
#
#     # Alias for backward compatibility
#     def action_view_partner_ledger(self):
#         """Alias for action_view_journal_entries"""
#         return self.action_view_journal_entries()


# models/aged_partner_inherit.py

# models/aged_partner_inherit.py

from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta


class AccountAgedTrialBalance(models.TransientModel):
    _inherit = 'account.aged.trial.balance'

    def show_details(self):
        """
        Show detailed aged balance breakdown with aging periods.
        """
        self.ensure_one()

        # Get the report parser to calculate aging
        report_lines = self._get_aging_data()

        # Clear existing detail lines
        self.env['account.aged.detail.line'].search([]).unlink()

        # Create detail lines
        DetailLine = self.env['account.aged.detail.line']
        detail_ids = []
        partners_with_overdue = 0

        for line_data in report_lines:
            vals = {
                'partner_id': line_data.get('partner_id'),
                'partner_name': line_data.get('partner_name'),
                'not_due': line_data.get('not_due', 0.0),
                'period_0': line_data.get('period_0', 0.0),
                'period_1': line_data.get('period_1', 0.0),
                'period_2': line_data.get('period_2', 0.0),
                'period_3': line_data.get('period_3', 0.0),
                'period_4': line_data.get('period_4', 0.0),
                'total': line_data.get('total', 0.0),
                'wizard_id': self.id,
            }
            detail_line = DetailLine.create(vals)
            detail_ids.append(detail_line.id)

            # Count partners with overdue amounts
            if any([vals['period_0'], vals['period_1'], vals['period_2'],
                    vals['period_3'], vals['period_4']]):
                partners_with_overdue += 1

        # Action name and context based on report type
        if self.result_selection == 'customer':
            action_name = _('Aged Receivable Details')
            report_type = 'customer'
            account_label = 'Receivable Accounts'
            partner_label = 'Customers'
        elif self.result_selection == 'supplier':
            action_name = _('Aged Payable Details')
            report_type = 'supplier'
            account_label = 'Payable Accounts'
            partner_label = 'Vendors'
        else:
            action_name = _('Aged Partner Balance Details')
            report_type = 'both'
            account_label = 'Receivable and Payable Accounts'
            partner_label = 'Partners'

        # Target move label
        target_move_label = 'All Posted Entries' if self.target_move == 'posted' else 'All Entries'

        # Build detailed action name with key info
        action_title = f"{action_name} - {self.date_from} ({self.period_length} days) - {len(detail_ids)} {partner_label}"

        return {
            'name': action_title,
            'type': 'ir.actions.act_window',
            'res_model': 'account.aged.detail.line',
            'view_mode': 'list,form',
            'domain': [('id', 'in', detail_ids)],
            'target': 'current',
            'context': {
                'create': False,
                'edit': False,
                'default_wizard_id': self.id,
            },
        }

    def _get_aging_data(self):
        """
        Calculate aging breakdown for each partner.
        """
        self.ensure_one()

        # Calculate period dates
        periods = self._calculate_periods()

        # Build domain for move lines
        domain = [
            ('account_id.account_type', 'in', self._get_account_types()),
            ('reconciled', '=', False),
            ('date', '<=', self.date_from),
        ]

        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))

        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))

        if self.target_move == 'posted':
            domain.append(('parent_state', '=', 'posted'))

        # Get all move lines
        move_lines = self.env['account.move.line'].search(domain)

        # Group by partner and calculate aging
        partner_data = {}
        for line in move_lines:
            partner_id = line.partner_id.id
            if partner_id not in partner_data:
                partner_data[partner_id] = {
                    'partner_id': partner_id,
                    'partner_name': line.partner_id.name,
                    'not_due': 0.0,
                    'period_0': 0.0,
                    'period_1': 0.0,
                    'period_2': 0.0,
                    'period_3': 0.0,
                    'period_4': 0.0,
                    'total': 0.0,
                }

            # Calculate amount (debit - credit for receivables, credit - debit for payables)
            if self.result_selection == 'customer':
                amount = line.debit - line.credit
            else:
                amount = line.credit - line.debit

            # Determine which aging bucket
            date_due = line.date_maturity or line.date
            period_key = self._get_period_key(date_due, periods)

            partner_data[partner_id][period_key] += amount
            partner_data[partner_id]['total'] += amount

        return list(partner_data.values())

    def _calculate_periods(self):
        """
        Calculate aging period dates.
        """
        periods = {}
        start_date = self.date_from

        for i in range(5):
            period_key = f'period_{4 - i}'
            end_date = start_date
            start_date = end_date - relativedelta(days=self.period_length - 1)

            periods[period_key] = {
                'start': start_date,
                'end': end_date,
            }

            start_date = start_date - relativedelta(days=1)

        # Not due (future dates)
        periods['not_due'] = {
            'start': self.date_from + relativedelta(days=1),
            'end': fields.Date.today() + relativedelta(years=10),
        }

        return periods

    def _get_period_key(self, date_due, periods):
        """
        Determine which period a date falls into.
        """
        if date_due > self.date_from:
            return 'not_due'

        for i in range(5):
            period_key = f'period_{i}'
            if periods[period_key]['start'] <= date_due <= periods[period_key]['end']:
                return period_key

        # Oldest period
        return 'period_4'

    def _get_account_types(self):
        """
        Get account types based on report selection.
        """
        if self.result_selection == 'customer':
            return ['asset_receivable']
        elif self.result_selection == 'supplier':
            return ['liability_payable']
        else:
            return ['asset_receivable', 'liability_payable']


class AccountAgedDetailLine(models.TransientModel):
    _name = 'account.aged.detail.line'
    _description = 'Aged Balance Detail Line'
    _order = 'total desc, partner_name'

    wizard_id = fields.Many2one('account.aged.trial.balance', string='Wizard', ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    partner_name = fields.Char(string='Partner Name', readonly=True)
    trust = fields.Selection(related='partner_id.trust', string='Trust', readonly=True, store=True)
    email = fields.Char(related='partner_id.email', string='Email', readonly=True)
    phone = fields.Char(related='partner_id.phone', string='Phone', readonly=True)
    vat = fields.Char(related='partner_id.vat', string='Tax ID', readonly=True)

    not_due = fields.Monetary(string='Not Due', readonly=True, currency_field='currency_id')
    period_0 = fields.Monetary(string='0-30', readonly=True, currency_field='currency_id')
    period_1 = fields.Monetary(string='31-60', readonly=True, currency_field='currency_id')
    period_2 = fields.Monetary(string='61-90', readonly=True, currency_field='currency_id')
    period_3 = fields.Monetary(string='91-120', readonly=True, currency_field='currency_id')
    period_4 = fields.Monetary(string='120+', readonly=True, currency_field='currency_id')
    total = fields.Monetary(string='Total', readonly=True, currency_field='currency_id')

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    def action_view_journal_entries(self):
        """
        View journal entries for this partner.
        """
        self.ensure_one()
        wizard = self.wizard_id

        domain = [
            ('partner_id', '=', self.partner_id.id),
            ('account_id.account_type', 'in', wizard._get_account_types()),
            ('reconciled', '=', False),
            ('date', '<=', wizard.date_from),
        ]

        if wizard.journal_ids:
            domain.append(('journal_id', 'in', wizard.journal_ids.ids))

        if wizard.target_move == 'posted':
            domain.append(('parent_state', '=', 'posted'))

        return {
            'name': _('Journal Entries: %s') % self.partner_name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': domain,
            'target': 'current',
        }

    # Alias for backward compatibility
    def action_view_partner_ledger(self):
        """Alias for action_view_journal_entries"""
        return self.action_view_journal_entries()