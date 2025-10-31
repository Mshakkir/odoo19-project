from odoo import models, fields, api

class GeneralLedgerDetailLine(models.TransientModel):
    _name = 'general.ledger.detail.line'
    _description = 'General Ledger Detail Line'

    wizard_id = fields.Many2one('account.report.general.ledger', string="Wizard", ondelete='cascade')

    account_id = fields.Many2one('account.account', string="Account")
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    partner_name = fields.Char(string="Partner")
    date = fields.Date(string="Date")
    move_name = fields.Char(string="Journal Entry")
    label = fields.Char(string="Label")

    debit = fields.Monetary(string="Debit", currency_field='currency_id')
    credit = fields.Monetary(string="Credit", currency_field='currency_id')
    balance = fields.Monetary(string="Balance", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    move_line_ids = fields.Many2many('account.move.line', string='Journal Items')
    is_summary_row = fields.Boolean(default=False)

    def open_move_lines(self):
        """Open detailed journal items for this account"""
        self.ensure_one()
        return {
            'name': f'Journal Items for {self.account_id.display_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.move_line_ids.ids)],
            'target': 'current',
        }
