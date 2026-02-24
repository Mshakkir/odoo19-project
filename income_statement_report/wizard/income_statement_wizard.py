# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class IncomeStatementWizard(models.TransientModel):
    _name = 'income.statement.wizard'
    _description = 'Income Statement Report Wizard'

    company_id = fields.Many2one(
        'res.company',
        string='CGS By using (Branch/Company)',
        default=lambda self: self.env.company,
        required=True,
    )
    all_companies = fields.Boolean(string='All', default=False)
    date_from = fields.Date(
        string='From',
        required=True,
        default=lambda self: fields.Date.today().replace(month=1, day=1),
    )
    date_to = fields.Date(
        string='To',
        required=True,
        default=fields.Date.today,
    )

    @api.onchange('all_companies')
    def _onchange_all_companies(self):
        if self.all_companies:
            self.company_id = False

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise ValidationError("'From' date must be earlier than 'To' date.")

    def _get_account_lines(self, account_types, company_ids):
        """
        Fetch summarized account move lines for given internal_group types.
        account_types: list of account.account internal_group values
                       e.g. ['income', 'expense', 'cost_of_revenue']
        Returns list of dicts: [{name, code, balance}, ...]
        """
        domain = [
            ('move_id.state', '=', 'posted'),
            ('move_id.date', '>=', self.date_from),
            ('move_id.date', '<=', self.date_to),
            ('account_id.account_type', 'in', account_types),
        ]
        if company_ids:
            domain.append(('company_id', 'in', company_ids))

        lines = self.env['account.move.line'].read_group(
            domain,
            fields=['account_id', 'balance'],
            groupby=['account_id'],
        )
        result = []
        for line in lines:
            account = self.env['account.account'].browse(line['account_id'][0])
            result.append({
                'name': account.name,
                'code': account.code,
                'balance': -line['balance'],  # negate: credit = positive income
            })
        return result

    def _build_report_data(self):
        if self.all_companies:
            company_ids = self.env['res.company'].search([]).ids
        else:
            company_ids = [self.company_id.id] if self.company_id else []

        # ---------- Income ----------
        income_lines = self._get_account_lines(
            ['income', 'income_other'], company_ids
        )
        total_income = sum(l['balance'] for l in income_lines)

        # ---------- Cost of Goods Sold ----------
        cogs_lines = self._get_account_lines(
            ['expense_direct_cost'], company_ids
        )
        # COGS balances are debit-positive, keep as positive cost
        for l in cogs_lines:
            l['balance'] = -l['balance']
        total_cogs = sum(l['balance'] for l in cogs_lines)

        gross_profit = total_income - total_cogs

        # ---------- Operating Expenses ----------
        expense_lines = self._get_account_lines(
            ['expense', 'expense_depreciation'], company_ids
        )
        for l in expense_lines:
            l['balance'] = -l['balance']
        total_expenses = sum(l['balance'] for l in expense_lines)

        net_profit = gross_profit - total_expenses

        return {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'company_name': 'All Companies' if self.all_companies else (self.company_id.name or ''),
            'income_lines': income_lines,
            'total_income': total_income,
            'cogs_lines': cogs_lines,
            'total_cogs': total_cogs,
            'gross_profit': gross_profit,
            'expense_lines': expense_lines,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
        }

    def action_show_report(self):
        data = self._build_report_data()
        return self.env.ref(
            'income_statement_report.action_income_statement_report'
        ).report_action(self, data=data)

    def action_clear(self):
        self.write({
            'date_from': fields.Date.today().replace(month=1, day=1),
            'date_to': fields.Date.today(),
            'all_companies': False,
            'company_id': self.env.company.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'income.statement.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }