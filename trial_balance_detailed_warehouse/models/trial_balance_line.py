from odoo import models, fields, api


class TrialBalanceLine(models.TransientModel):
    """Trial Balance Detail Line with drill-down capability."""

    _name = 'trial.balance.line'
    _description = 'Trial Balance Line'

    wizard_id = fields.Many2one('account.balance.report', string='Wizard', required=True, ondelete='cascade')
    account_id = fields.Many2one('account.account', string='Account', required=True)
    account_code = fields.Char(string='Account Code')
    account_name = fields.Char(string='Account Name')

    opening_balance = fields.Float(string='Opening Balance', digits=(16, 2))
    debit = fields.Float(string='Debit', digits=(16, 2))
    credit = fields.Float(string='Credit', digits=(16, 2))
    ending_balance = fields.Float(string='Ending Balance', digits=(16, 2))

    company_currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    # Store related move line IDs
    move_line_ids = fields.Many2many(
        'account.move.line',
        'trial_balance_line_move_line_rel',
        'tb_line_id',
        'move_line_id',
        string='Journal Items'
    )

    move_line_count = fields.Integer(string='Journal Items', compute='_compute_move_line_count')

    @api.depends('move_line_ids')
    def _compute_move_line_count(self):
        for record in self:
            record.move_line_count = len(record.move_line_ids)

    def action_view_journal_items(self):
        """Open journal items for this account filtered by wizard criteria."""
        self.ensure_one()

        # Get analytic filter from wizard
        analytic_ids = self.wizard_id.analytic_account_ids.ids if self.wizard_id.analytic_account_ids else []

        # Use stored move_line_ids
        domain = [('id', 'in', self.move_line_ids.ids)] if self.move_line_ids else []

        # Prepare context
        ctx = dict(self.env.context)
        ctx.update({
            'search_default_group_by_move': 1,
            'analytic_filter_ids': analytic_ids,
        })

        return {
            'name': f'Journal Items - {self.account_code} {self.account_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': domain,
            'context': ctx,
            'target': 'current',
        }

    def action_view_journal_entries(self):
        """Open journal entries related to this account."""
        self.ensure_one()

        move_ids = self.move_line_ids.mapped('move_id').ids

        return {
            'name': f'Journal Entries - {self.account_code} {self.account_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', move_ids)],
            'target': 'current',
        }