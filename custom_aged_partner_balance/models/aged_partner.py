import time
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAgedTrialBalanceInherited(models.TransientModel):
    """
    Inherit OdooMates Aged Trial Balance Wizard
    Add Show Details functionality
    """
    _inherit = 'account.aged.trial.balance'

    # Add partner_ids field if not exists in parent
    partner_ids = fields.Many2many(
        'res.partner',
        string='Partners',
        help='Filter by specific partners. Leave empty for all partners.'
    )

    def show_details(self):
        """
        Open detailed view of aged partner balance
        """
        self.ensure_one()

        # Get report data using parent method
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': self.read()[0]
        }
        data = self._get_report_data(data)

        # Get detailed partner lines
        report = self.env['report.accounting_pdf_reports.report_agedpartnerbalance']

        # Determine account types based on result_selection
        if self.result_selection == 'customer':
            account_type = ['asset_receivable']
        elif self.result_selection == 'supplier':
            account_type = ['liability_payable']
        else:
            account_type = ['liability_payable', 'asset_receivable']

        # Get partner move lines with details
        movelines, total, dummy = report._get_partner_move_lines(
            account_type,
            self.partner_ids.ids if self.partner_ids else [],
            self.date_from,
            self.target_move,
            self.period_length
        )

        # Create detail records
        detail_obj = self.env['account.aged.detail.line']
        # Clear previous details for this wizard
        detail_obj.search([('wizard_id', '=', self.id)]).unlink()

        detail_lines = []
        for partner_data in movelines:
            vals = {
                'wizard_id': self.id,
                'partner_id': partner_data.get('partner_id'),
                'partner_name': partner_data.get('name'),
                'trust': partner_data.get('trust', 'normal'),
                'not_due': partner_data.get('direction', 0.0),
                'period_0': partner_data.get('0', 0.0),
                'period_1': partner_data.get('1', 0.0),
                'period_2': partner_data.get('2', 0.0),
                'period_3': partner_data.get('3', 0.0),
                'period_4': partner_data.get('4', 0.0),
                'total': partner_data.get('total', 0.0),
            }
            detail_lines.append(detail_obj.create(vals))

        # Open list view with details
        return {
            'name': _('Aged Balance Details - %s') % (
                'Receivable' if self.result_selection == 'customer'
                else 'Payable' if self.result_selection == 'supplier'
                else 'Partner Balance'
            ),
            'type': 'ir.actions.act_window',
            'res_model': 'account.aged.detail.line',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('custom_aged_partner_balance.view_aged_detail_list').id, 'list'),
                (self.env.ref('custom_aged_partner_balance.view_aged_detail_form').id, 'form')
            ],
            'domain': [('wizard_id', '=', self.id)],
            'context': {
                'default_wizard_id': self.id,
                'period_names': {
                    '0': data['form']['0']['name'],
                    '1': data['form']['1']['name'],
                    '2': data['form']['2']['name'],
                    '3': data['form']['3']['name'],
                    '4': data['form']['4']['name'],
                },
                'result_selection': self.result_selection,
                'date_from': self.date_from,
            },
            'target': 'current',
        }


class AccountAgedDetailLine(models.TransientModel):
    """Temporary model to store detailed aged balance lines"""
    _name = 'account.aged.detail.line'
    _description = 'Aged Balance Detail Line'
    _order = 'total desc, partner_name'

    wizard_id = fields.Many2one(
        'account.aged.trial.balance',
        string='Wizard',
        ondelete='cascade',
        required=True
    )
    partner_id = fields.Many2one('res.partner', string='Partner')
    partner_name = fields.Char(string='Partner Name', required=True)

    trust = fields.Selection([
        ('good', 'Good Debtor'),
        ('normal', 'Normal Debtor'),
        ('bad', 'Bad Debtor')
    ], string='Trust', default='normal')

    # Aging columns
    not_due = fields.Float(string='Not Due', digits='Account')
    period_0 = fields.Float(string='Period 0', digits='Account')
    period_1 = fields.Float(string='Period 1', digits='Account')
    period_2 = fields.Float(string='Period 2', digits='Account')
    period_3 = fields.Float(string='Period 3', digits='Account')
    period_4 = fields.Float(string='Period 4', digits='Account')
    total = fields.Float(string='Total', digits='Account')

    # Additional partner information
    email = fields.Char(related='partner_id.email', string='Email', readonly=True)
    phone = fields.Char(related='partner_id.phone', string='Phone', readonly=True)
    mobile = fields.Char(related='partner_id.mobile', string='Mobile', readonly=True)
    vat = fields.Char(related='partner_id.vat', string='Tax ID', readonly=True)
    street = fields.Char(related='partner_id.street', string='Street', readonly=True)
    city = fields.Char(related='partner_id.city', string='City', readonly=True)
    country_id = fields.Many2one(related='partner_id.country_id', string='Country', readonly=True)

    # Computed fields for better analysis
    overdue_amount = fields.Float(
        string='Total Overdue',
        compute='_compute_overdue',
        store=True,
        help='Sum of all overdue periods (0-4)'
    )

    is_overdue = fields.Boolean(
        string='Has Overdue',
        compute='_compute_overdue',
        store=True
    )

    @api.depends('period_0', 'period_1', 'period_2', 'period_3', 'period_4')
    def _compute_overdue(self):
        for record in self:
            record.overdue_amount = (
                    record.period_0 + record.period_1 +
                    record.period_2 + record.period_3 + record.period_4
            )
            record.is_overdue = record.overdue_amount != 0

    def action_view_partner_ledger(self):
        """Open partner ledger for detailed transactions"""
        self.ensure_one()

        # Determine account types
        if self.wizard_id.result_selection == 'customer':
            account_types = ['asset_receivable']
        elif self.wizard_id.result_selection == 'supplier':
            account_types = ['liability_payable']
        else:
            account_types = ['asset_receivable', 'liability_payable']

        return {
            'name': _('Partner Ledger - %s') % self.partner_name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': [
                ('partner_id', '=', self.partner_id.id),
                ('account_id.account_type', 'in', account_types),
                ('parent_state', '=', 'posted') if self.wizard_id.target_move == 'posted' else ('id', '!=', False),
            ],
            'context': {
                'default_partner_id': self.partner_id.id,
                'search_default_group_by_move': 1,
            },
        }

    def action_view_partner_invoices(self):
        """Open partner invoices"""
        self.ensure_one()

        # Determine move types
        if self.wizard_id.result_selection == 'customer':
            move_types = ['out_invoice', 'out_refund']
        elif self.wizard_id.result_selection == 'supplier':
            move_types = ['in_invoice', 'in_refund']
        else:
            move_types = ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']

        return {
            'name': _('Invoices - %s') % self.partner_name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('partner_id', '=', self.partner_id.id),
                ('move_type', 'in', move_types),
                ('state', '=', 'posted') if self.wizard_id.target_move == 'posted' else ('id', '!=', False),
            ],
            'context': {
                'default_partner_id': self.partner_id.id,
            },
        }

    def action_open_partner(self):
        """Open partner form"""
        self.ensure_one()
        return {
            'name': _('Partner: %s') % self.partner_name,
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'res_id': self.partner_id.id,
            'target': 'current',
        }