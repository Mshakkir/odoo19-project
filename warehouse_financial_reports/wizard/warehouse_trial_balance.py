from odoo import fields, models, api, _
from odoo.exceptions import UserError


class WarehouseTrialBalance(models.TransientModel):
    _name = 'warehouse.trial.balance'
    _description = 'Warehouse Trial Balance Wizard'

    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date', required=True, default=fields.Date.today)

    target_move = fields.Selection([
        ('posted', 'All Posted Entries'),
        ('all', 'All Entries')
    ], string='Target Moves', required=True, default='posted')

    display_account = fields.Selection([
        ('all', 'All accounts'),
        ('movement', 'With movements'),
        ('not_zero', 'With balance not equal to zero')
    ], string='Display Accounts', required=True, default='not_zero')

    journal_ids = fields.Many2many(
        'account.journal',
        'warehouse_tb_journal_rel',
        'wizard_id',
        'journal_id',
        string='Journals',
        required=True,
        default=lambda self: self.env['account.journal'].search([])
    )

    report_mode = fields.Selection([
        ('single', 'Single Warehouse Report'),
        ('consolidated', 'Consolidated (All Warehouses Combined)')
    ], string='Report Mode', required=True, default='single')

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Select Warehouse',
        help='Select specific warehouse for single report'
    )

    @api.onchange('report_mode')
    def _onchange_report_mode(self):
        """Clear warehouse if consolidated report selected"""
        if self.report_mode == 'consolidated':
            self.analytic_account_id = False

    def print_report(self):
        """Generate trial balance report"""
        self.ensure_one()
        if self.report_mode == 'single' and not self.analytic_account_id:
            raise UserError(_('Please select a warehouse for single warehouse report.'))

        data = self._prepare_report_data()
        if self.report_mode == 'single':
            data['form']['analytic_account_ids'] = [self.analytic_account_id.id]
            data['form']['warehouse_name'] = self.analytic_account_id.name
            data['form']['report_mode'] = 'single'
        else:
            data['form']['analytic_account_ids'] = []
            data['form']['warehouse_name'] = 'All Warehouses (Consolidated)'
            data['form']['report_mode'] = 'consolidated'

        return self.env.ref('warehouse_financial_reports.action_warehouse_trial_balance').report_action(
            self, data={'form': data['form']}
        )

    def _prepare_report_data(self):
        """Prepare common data"""
        used_context = {
            'journal_ids': self.journal_ids.ids,
            'state': self.target_move,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'strict_range': True,
        }

        return {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date_from': self.date_from,
                'date_to': self.date_to,
                'target_move': self.target_move,
                'display_account': self.display_account,
                'journal_ids': self.journal_ids.ids,
                'used_context': used_context,
            }
        }
