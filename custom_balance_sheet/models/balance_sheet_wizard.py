# custom_balance_sheet/models/balance_sheet_wizard.py
from odoo import api, fields, models, _
import uuid
from datetime import datetime

class BalanceSheetWizard(models.TransientModel):
    _name = "balance.sheet.wizard"
    _description = "Balance Sheet Wizard"

    move_scope = fields.Selection([
        ('all', 'All Entries'),
        ('posted', 'All Posted Entries'),
    ], string="Target Moves", required=True, default='posted')
    date_from = fields.Date(string="Date from", required=True)
    date_to = fields.Date(string="Date to", required=True)
    wizard_uuid = fields.Char(string="Wizard UUID", readonly=True)

    def _ensure_uuid(self):
        if not self.wizard_uuid:
            self.wizard_uuid = str(uuid.uuid4())
            self.write({'wizard_uuid': self.wizard_uuid})

    def _build_aml_domain(self):
        domain = [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        if self.move_scope == 'posted':
            domain += [('move_id.state', '=', 'posted')]
        return domain

    def action_view_details(self):
        """
        Aggregate account.move.line by account and create balance.sheet.line records tagged with wizard_uuid.
        Then open a tree view of those lines.
        """
        self._ensure_uuid()
        domain = self._build_aml_domain()
        aml_model = self.env['account.move.line']
        # use read_group to aggregate by account_id
        group_fields = ['account_id']
        aggregated = aml_model.read_group(domain + [('account_id', '!=', False)],
                                        ['account_id', 'debit', 'credit', 'balance'],
                                        group_fields)
        # purge previous lines for this uuid (optional)
        self.env['balance.sheet.line'].search([('wizard_uuid', '=', self.wizard_uuid)]).unlink()
        # Create lines
        for rec in aggregated:
            account = rec.get('account_id') and rec.get('account_id')[0] or False
            # rec has fields: account_id, debit, credit, balance
            self.env['balance.sheet.line'].create({
                'wizard_uuid': self.wizard_uuid,
                'account_id': account,
                'debit': rec.get('debit') or 0.0,
                'credit': rec.get('credit') or 0.0,
                'balance': rec.get('balance') or 0.0,
            })

        # Open action
        action = {
            'name': _('Balance Sheet Details'),
            'res_model': 'balance.sheet.line',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'domain': [('wizard_uuid', '=', self.wizard_uuid)],
            'context': {
                'default_wizard_uuid': self.wizard_uuid,
                'search_default_group_by_account': 1,
            },
        }
        return action

    def action_print_pdf(self):
        """
        Return report action for our QWeb template. We pass the wizard_uuid and filters in data for report model.
        """
        self._ensure_uuid()
        data = {
            'wizard_uuid': self.wizard_uuid,
            'move_scope': self.move_scope,
            'date_from': str(self.date_from),
            'date_to': str(self.date_to),
        }
        return self.env.ref('accounting_pdf_reports.action_report_financial').report_action(self, data=data)