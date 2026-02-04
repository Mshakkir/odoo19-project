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
                'name': (i != 0 and (str((5 - (i + 1)) * period_length) + '-' + str((5 - i) * period_length)) or (
                            '+' + str(4 * period_length))),
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


class ReportAgedPartnerBalance(models.AbstractModel):
    _inherit = 'report.accounting_pdf_reports.report_agedpartnerbalance'

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Override to add partners_with_overdue and total_partners counts
        """
        # Get the original report values
        if hasattr(super(), '_get_report_values'):
            result = super()._get_report_values(docids, data)
        else:
            result = {}

        # Get partner lines from the report
        if 'get_partner_lines' in result:
            partner_lines = result['get_partner_lines']
        else:
            # Fallback: try to get it from the original method
            partner_lines = self._get_partner_move_lines(
                data.get('form', {}).get('account_ids', []),
                data.get('form', {}).get('date_from'),
                data.get('form', {}).get('target_move'),
                data.get('form', {}).get('period_length', 30),
                data.get('form', {})
            ) if hasattr(self, '_get_partner_move_lines') else []

        # Calculate partners with overdue
        partners_with_overdue = 0
        total_partners = len(partner_lines) if partner_lines else 0

        for partner in partner_lines:
            # Check if partner has any overdue amounts (periods 0-4)
            # Period keys: '0', '1', '2', '3', '4'
            has_overdue = False
            for period_key in ['0', '1', '2', '3', '4']:
                if partner.get(period_key, 0.0) != 0.0:
                    has_overdue = True
                    break

            if has_overdue:
                partners_with_overdue += 1

        # Add to result
        result['partners_with_overdue'] = partners_with_overdue
        result['total_partners'] = total_partners

        # Calculate percentage breakdown for aging analysis
        if 'get_direction' in result:
            direction = result['get_direction']
            total = direction[5] if len(direction) > 5 else 0  # Total amount

            percentage_breakdown = {}
            if total and total != 0:
                # Not due
                percentage_breakdown['not_due'] = (direction[6] / total * 100) if len(direction) > 6 else 0
                # Periods 0-4
                for i in range(5):
                    if len(direction) > i:
                        percentage_breakdown[f'period_{i}'] = (direction[i] / total * 100)
                    else:
                        percentage_breakdown[f'period_{i}'] = 0
            else:
                percentage_breakdown = {
                    'not_due': 0,
                    'period_0': 0,
                    'period_1': 0,
                    'period_2': 0,
                    'period_3': 0,
                    'period_4': 0,
                }

            result['percentage_breakdown'] = percentage_breakdown

        return result