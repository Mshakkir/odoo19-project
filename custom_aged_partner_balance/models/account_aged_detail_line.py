from odoo import models, fields, api


class AccountAgedDetailLine(models.TransientModel):
    _name = 'account.aged.detail.line'
    _description = 'Aged Balance Detail Line'

    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    partner_name = fields.Char(string='Partner Name', readonly=True)
    trust = fields.Selection([
        ('good', 'Good Debtor'),
        ('normal', 'Normal Debtor'),
        ('bad', 'Bad Debtor')
    ], string='Trust', readonly=True)
    email = fields.Char(string='Email', readonly=True)
    phone = fields.Char(string='Phone', readonly=True)
    vat = fields.Char(string='Tax ID', readonly=True)

    # Aging period fields
    not_due = fields.Monetary(string='Not Due', readonly=True, currency_field='currency_id')
    period_0 = fields.Monetary(string='0-30', readonly=True, currency_field='currency_id')
    period_1 = fields.Monetary(string='31-60', readonly=True, currency_field='currency_id')
    period_2 = fields.Monetary(string='61-90', readonly=True, currency_field='currency_id')
    period_3 = fields.Monetary(string='91-120', readonly=True, currency_field='currency_id')
    period_4 = fields.Monetary(string='120+', readonly=True, currency_field='currency_id')
    total = fields.Monetary(string='Total', readonly=True, currency_field='currency_id')

    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    def action_view_journal_entries(self):
        """Open journal entries for this partner"""
        self.ensure_one()

        # Get the date range from context or calculate based on aging
        action = self.env.ref('account.action_move_journal_line').read()[0]
        action['domain'] = [
            ('partner_id', '=', self.partner_id.id),
            ('account_id.account_type', 'in', ['asset_receivable', 'liability_payable']),
            ('parent_state', '=', 'posted')
        ]
        action['context'] = {
            'search_default_partner_id': self.partner_id.id,
            'default_partner_id': self.partner_id.id,
        }
        return action