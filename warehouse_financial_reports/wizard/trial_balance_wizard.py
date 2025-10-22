from odoo import api, fields, models

class TrialBalanceWizard(models.TransientModel):
    _name = 'trial.balance.wizard'
    _description = 'Trial Balance Wizard'

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')

    def generate_trial_balance(self):
        domain = [('move_id.state', '=', 'posted')]
        if self.date_from:
            domain += [('date', '>=', self.date_from)]
        if self.date_to:
            domain += [('date', '<=', self.date_to)]
        if self.warehouse_id:
            domain += [('warehouse_id', '=', self.warehouse_id.id)]

        lines = self.env['account.move.line'].search(domain)
        # Prepare data for the report
        data = []
        for line in lines:
            data.append({
                'account': line.account_id.name,
                'debit': line.debit,
                'credit': line.credit,
                'balance': line.debit - line.credit,
            })

        return self.env.ref('warehouse_financial_reports.trial_balance_report').report_action(self, data=data)
