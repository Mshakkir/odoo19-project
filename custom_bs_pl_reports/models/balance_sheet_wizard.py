from odoo import models, fields, api

class BalanceSheetWizard(models.TransientModel):
    _name = "balance.sheet.wizard"
    _description = "Balance Sheet / P&L Wizard"

    report_type = fields.Selection([
        ('balance_sheet', 'Balance Sheet'),
        ('profit_loss', 'Profit & Loss')
    ], string="Report Type", required=True)
    date_from = fields.Date(string="Start Date")
    date_to = fields.Date(string="End Date")
    target_move = fields.Selection([
        ('posted', 'All Posted Entries'),
        ('all', 'All Entries')
    ], string="Target Moves", default='posted')

    # Lines to display
    line_ids = fields.One2many("balance.sheet.line", "wizard_id", string="Report Lines")

    def action_generate_report(self):
        """Populate the report lines"""
        self.ensure_one()
        domain = []
        if self.target_move == 'posted':
            domain.append(('move_id.state', '=', 'posted'))
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))

        # Filter accounts based on report type
        if self.report_type == 'balance_sheet':
            accounts = self.env['account.account'].search([('user_type_id.type', 'in', ['asset','liability'])])
        else:
            accounts = self.env['account.account'].search([('user_type_id.type', 'in', ['income','expense'])])

        lines = []
        for acc in accounts:
            move_lines = self.env['account.move.line'].search([('account_id', '=', acc.id)] + domain)
            debit = sum(move_lines.mapped('debit'))
            credit = sum(move_lines.mapped('credit'))
            balance = debit - credit
            lines.append((0,0,{
                'account_id': acc.id,
                'code': acc.code,
                'name': acc.name,
                'balance': balance,
            }))
        self.line_ids = lines
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'balance.sheet.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_view_ledger(self):
        """Open ledger for accounts in report"""
        account_ids = self.line_ids.mapped('account_id').ids
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ledger Entries',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': [('account_id', 'in', account_ids)],
            'target': 'current',
        }


class BalanceSheetLine(models.TransientModel):
    _name = "balance.sheet.line"
    _description = "Balance Sheet / P&L Line"

    wizard_id = fields.Many2one("balance.sheet.wizard")
    account_id = fields.Many2one("account.account", string="Account")
    code = fields.Char(string="Code")
    name = fields.Char(string="Account Name")
    balance = fields.Float(string="Balance")
