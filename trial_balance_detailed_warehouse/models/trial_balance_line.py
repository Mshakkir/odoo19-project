from odoo import models, fields, api


class TrialBalanceLine(models.TransientModel):
    """Trial Balance Detail Line with drill-down capability."""

    _name = 'trial.balance.line'
    _description = 'Trial Balance Line'
    _order = 'account_id'

    wizard_id = fields.Many2one('account.balance.report', string='Wizard', required=True, ondelete='cascade')
    account_id = fields.Many2one('account.account', string='Account', required=True)
    account_code = fields.Char(related='account_id.code', string='Account Code', store=True)
    account_name = fields.Char(related='account_id.name', string='Account Name', store=True)

    opening_balance = fields.Monetary(string='Opening Balance', currency_field='company_currency_id')
    debit = fields.Monetary(string='Debit', currency_field='company_currency_id')
    credit = fields.Monetary(string='Credit', currency_field='company_currency_id')
    ending_balance = fields.Monetary(string='Ending Balance', currency_field='company_currency_id')

    company_currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    # Store related move lines for drill-down
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

        # If we have stored move_line_ids, use them (already filtered)
        if self.move_line_ids:
            domain = [('id', 'in', self.move_line_ids.ids)]
        else:
            # Build domain based on wizard criteria
            domain = [
                ('account_id', '=', self.account_id.id),
                ('move_id.state', '=', 'posted'),
            ]

            if self.wizard_id.date_from:
                domain.append(('date', '>=', self.wizard_id.date_from))
            if self.wizard_id.date_to:
                domain.append(('date', '<=', self.wizard_id.date_to))

        # Prepare context
        ctx = dict(self.env.context)
        ctx.update({
            'search_default_group_by_move': 1,  # Group by journal entry
            'analytic_filter_ids': analytic_ids,  # Pass for highlighting
        })

        return {
            'name': f'Journal Items - {self.account_id.code} {self.account_id.name}',
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
            'name': f'Journal Entries - {self.account_id.code} {self.account_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', move_ids)],
            'target': 'current',
        }