import time
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAgedTrialBalanceCustom(models.TransientModel):
    _name = 'account.aged.trial.balance.custom'
    _inherit = 'account.common.partner.report'
    _description = 'Custom Account Aged Trial Balance Report'

    period_length = fields.Integer(
        string='Period Length (days)',
        required=True,
        default=30
    )
    journal_ids = fields.Many2many(
        'account.journal',
        string='Journals',
        required=True
    )
    date_from = fields.Date(
        default=lambda *a: time.strftime('%Y-%m-%d')
    )

    # Custom partner field with dynamic domain
    partner_ids = fields.Many2many(
        'res.partner',
        'aged_balance_partner_rel',
        'wizard_id',
        'partner_id',
        string='Partners',
        domain="[]"  # Will be set dynamically
    )

    @api.onchange('result_selection')
    def _onchange_result_selection(self):
        """
        Update partner domain based on result_selection
        """
        if self.result_selection == 'customer':
            # Show only customers
            return {
                'domain': {
                    'partner_ids': [('customer_rank', '>', 0)]
                }
            }
        elif self.result_selection == 'supplier':
            # Show only vendors/suppliers
            return {
                'domain': {
                    'partner_ids': [('supplier_rank', '>', 0)]
                }
            }
        else:
            # Show all partners (customers and suppliers)
            return {
                'domain': {
                    'partner_ids': ['|', ('customer_rank', '>', 0), ('supplier_rank', '>', 0)]
                }
            }

    @api.model
    def default_get(self, fields_list):
        """
        Set default values based on context
        """
        res = super(AccountAgedTrialBalanceCustom, self).default_get(fields_list)

        # Set result_selection from context
        if self._context.get('default_result_selection'):
            res['result_selection'] = self._context.get('default_result_selection')

        # Set default journals - all journals
        if 'journal_ids' in fields_list:
            journals = self.env['account.journal'].search([
                ('company_id', '=', self.env.company.id)
            ])
            res['journal_ids'] = journals.ids

        return res

    def _get_report_data(self, data):
        """
        Prepare report data with aging periods
        """
        res = {}
        data = self.pre_print_report(data)
        data['form'].update(self.read(['period_length'])[0])
        period_length = data['form']['period_length']

        if period_length <= 0:
            raise UserError(_('You must set a period length greater than 0.'))
        if not data['form']['date_from']:
            raise UserError(_('You must set a start date.'))

        start = data['form']['date_from']

        # Create 5 aging periods
        for i in range(5)[::-1]:
            stop = start - relativedelta(days=period_length - 1)
            res[str(i)] = {
                'name': (
                        i != 0 and
                        (str((5 - (i + 1)) * period_length) + '-' + str((5 - i) * period_length)) or
                        ('+' + str(4 * period_length))
                ),
                'stop': start.strftime('%Y-%m-%d'),
                'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
            }
            start = stop - relativedelta(days=1)

        data['form'].update(res)

        # Add partner_ids to form data
        if self.partner_ids:
            data['form']['partner_ids'] = self.partner_ids.ids

        return data

    def _print_report(self, data):
        """
        Print the custom report
        """
        data = self._get_report_data(data)

        # Use the custom report template
        return self.env.ref('custom_aged_partner_balance.action_report_aged_partner_balance_custom'). \
            with_context(landscape=True).report_action(self, data=data)

    def check_report(self):
        """
        Validate and generate report
        """
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read([
            'date_from',
            'period_length',
            'result_selection',
            'target_move',
            'partner_ids'
        ])[0]

        # Convert partner_ids to list of IDs if it's a recordset
        if 'partner_ids' in data['form']:
            data['form']['partner_ids'] = data['form']['partner_ids']

        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')

        return self._print_report(data)