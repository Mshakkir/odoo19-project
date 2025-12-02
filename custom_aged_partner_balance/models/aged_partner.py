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
    partner_ids = fields.Many2many('res.partner', string='Partners')

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
        return self.env.ref('accounting_pdf_reports.action_report_aged_partner_balance'). \
            with_context(landscape=True).report_action(self, data=data)

    def show_details(self):
        """
        Open detailed view of aged partner balance
        """
        self.ensure_one()

        # Get report data
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': self.read()[0]
        }
        data = self._get_report_data(data)

        # Get detailed partner lines
        report = self.env['report.accounting_pdf_reports.report_agedpartnerbalance']

        # Determine account types based on result_selection
        if self.result_selection == 'customer':
            account_type = ['receivable']
        elif self.result_selection == 'supplier':
            account_type = ['payable']
        else:
            account_type = ['payable', 'receivable']

        # Get partner move lines with details
        movelines, total, dummy = report._get_partner_move_lines(
            account_type,
            self.partner_ids.ids if self.partner_ids else [],
            self.date_from,
            self.target_move,
            self.period_length
        )

        # Create detail records
        detail_obj = self.env['account.aged.detail.line']
        detail_obj.search([]).unlink()  # Clear previous details

        detail_lines = []
        for partner_data in movelines:
            vals = {
                'wizard_id': self.id,
                'partner_id': partner_data.get('partner_id'),
                'partner_name': partner_data.get('name'),
                'trust': partner_data.get('trust', 'normal'),
                'not_due': partner_data.get('direction', 0.0),
                'period_0': partner_data.get('0', 0.0),
                'period_1': partner_data.get('1', 0.0),
                'period_2': partner_data.get('2', 0.0),
                'period_3': partner_data.get('3', 0.0),
                'period_4': partner_data.get('4', 0.0),
                'total': partner_data.get('total', 0.0),
            }
            detail_lines.append(detail_obj.create(vals))

        # Open tree view with details
        return {
            'name': _('Aged Balance Details - %s') % (
                'Receivable' if self.result_selection == 'customer'
                else 'Payable' if self.result_selection == 'supplier'
                else 'Partner Balance'
            ),
            'type': 'ir.actions.act_window',
            'res_model': 'account.aged.detail.line',
            'view_mode': 'list,form',
            'view_id': self.env.ref('custom_aged_partner_balance.view_aged_detail_tree').id,
            'domain': [('wizard_id', '=', self.id)],
            'context': {
                'default_wizard_id': self.id,
                'period_names': {
                    '0': data['form']['0']['name'],
                    '1': data['form']['1']['name'],
                    '2': data['form']['2']['name'],
                    '3': data['form']['3']['name'],
                    '4': data['form']['4']['name'],
                },
                'result_selection': self.result_selection,
            },
            'target': 'current',
        }


class AccountAgedDetailLine(models.TransientModel):
    """Temporary model to store detailed aged balance lines"""
    _name = 'account.aged.detail.line'
    _description = 'Aged Balance Detail Line'
    _order = 'total desc, partner_name'

    wizard_id = fields.Many2one('account.aged.trial.balance', string='Wizard', ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Partner')
    partner_name = fields.Char(string='Partner Name')
    trust = fields.Selection([
        ('good', 'Good Debtor'),
        ('normal', 'Normal Debtor'),
        ('bad', 'Bad Debtor')
    ], string='Trust', default='normal')

    not_due = fields.Float(string='Not Due', digits='Account')
    period_0 = fields.Float(string='Period 0', digits='Account')
    period_1 = fields.Float(string='Period 1', digits='Account')
    period_2 = fields.Float(string='Period 2', digits='Account')
    period_3 = fields.Float(string='Period 3', digits='Account')
    period_4 = fields.Float(string='Period 4', digits='Account')
    total = fields.Float(string='Total', digits='Account')

    # Additional partner information
    email = fields.Char(related='partner_id.email', string='Email')
    phone = fields.Char(related='partner_id.phone', string='Phone')
    vat = fields.Char(related='partner_id.vat', string='Tax ID')

    def action_view_partner_ledger(self):
        """Open partner ledger for detailed transactions"""
        self.ensure_one()
        return {
            'name': _('Partner Ledger - %s') % self.partner_name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'tree',
            'domain': [
                ('partner_id', '=', self.partner_id.id),
                ('account_id.account_type', 'in',
                 ['asset_receivable'] if self.wizard_id.result_selection == 'customer'
                 else ['liability_payable'] if self.wizard_id.result_selection == 'supplier'
                 else ['asset_receivable', 'liability_payable']),
            ],
            'context': {'default_partner_id': self.partner_id.id},
        }