from odoo import models, fields, api


class AccountingReport(models.TransientModel):
    _inherit = 'accounting.report'

    def action_view_details(self):
        """Open ledger entries depending on report type."""
        self.ensure_one()
        report_type = self.env.context.get('report_type')
        accounts = self.account_report_id.get_all_accounts()  # Get accounts of this report

        if report_type == 'balance_sheet':
            domain = [('account_id', 'in', accounts.ids),
                      ('account_id.user_type_id.type', 'in', ['asset', 'liability'])]
            view_name = 'Balance Sheet Ledger'
        else:  # Profit & Loss
            domain = [('account_id', 'in', accounts.ids),
                      ('account_id.user_type_id.type', 'in', ['income', 'expense'])]
            view_name = 'Profit & Loss Ledger'

        return {
            'type': 'ir.actions.act_window',
            'name': view_name,
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': domain,
            'target': 'current',
        }
