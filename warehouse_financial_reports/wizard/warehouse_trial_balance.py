# wizard/warehouse_trial_balance.py
# ==========================================
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class WarehouseTrialBalance(models.TransientModel):
    _name = 'warehouse.trial.balance'
    _description = 'Warehouse Trial Balance Wizard'

    date_from = fields.Date(string='Start Date', required=True)
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
        string='Journals',
        required=True,
        default=lambda self: self.env['account.journal'].search([])
    )

    # Key field: Select which warehouse to report on
    report_mode = fields.Selection([
        ('single', 'Single Warehouse Report'),
        ('all_separate', 'All Warehouses (Separate Reports)'),
        ('consolidated', 'Consolidated (All Warehouses Combined)')
    ], string='Report Mode', required=True, default='single')

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Select Warehouse',
        help='Select specific warehouse for single report'
    )

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string='Warehouses',
        help='Select warehouses for separate or consolidated reports',
        default=lambda self: self.env['account.analytic.account'].search([])
    )

    @api.onchange('report_mode')
    def _onchange_report_mode(self):
        """Show/hide fields based on report mode"""
        if self.report_mode == 'single':
            return {'domain': {'analytic_account_id': []}}
        else:
            self.analytic_account_id = False

    def print_report(self):
        """Generate trial balance report based on selected mode"""
        self.ensure_one()

        if self.report_mode == 'single':
            if not self.analytic_account_id:
                raise UserError(_('Please select a warehouse for single warehouse report.'))
            return self._print_single_warehouse_report()

        elif self.report_mode == 'all_separate':
            if not self.analytic_account_ids:
                raise UserError(_('Please select warehouses for separate reports.'))
            return self._print_all_separate_reports()

        else:  # consolidated
            return self._print_consolidated_report()

    def _print_single_warehouse_report(self):
        """Generate report for single warehouse"""
        data = self._prepare_report_data()
        data['form']['analytic_account_ids'] = [self.analytic_account_id.id]
        data['form']['warehouse_name'] = self.analytic_account_id.name
        data['form']['report_mode'] = 'single'

        return self.env.ref('warehouse_financial_reports.action_warehouse_trial_balance').report_action(
            self, data={'form': data['form']}
        )

    def _print_all_separate_reports(self):
        """Generate separate reports for each selected warehouse"""
        # This will generate multiple PDF reports
        reports = []

        for analytic in self.analytic_account_ids:
            data = self._prepare_report_data()
            data['form']['analytic_account_ids'] = [analytic.id]
            data['form']['warehouse_name'] = analytic.name
            data['form']['report_mode'] = 'single'

            report = self.env.ref('warehouse_financial_reports.action_warehouse_trial_balance').report_action(
                self, data=data
            )
            reports.append(report)

        # Return the first report (in practice, you might want to merge PDFs)
        return reports[0] if reports else {}

    def _print_consolidated_report(self):
        """Generate consolidated report for all warehouses"""
        data = self._prepare_report_data()
        data['form']['analytic_account_ids'] = []
        data['form']['warehouse_name'] = 'All Warehouses (Consolidated)'
        data['form']['report_mode'] = 'consolidated'

        return self.env.ref('warehouse_financial_reports.action_warehouse_trial_balance').report_action(
            self, data={'form': data['form']}
        )

    def _prepare_report_data(self):
        """Prepare common data for all report types"""
        # Build context for filtering
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