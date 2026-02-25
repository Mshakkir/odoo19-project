# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class IncomeStatementWizard(models.TransientModel):
    _name = 'income.statement.wizard'
    _description = 'Income Statement Report Wizard'

    company_id = fields.Many2one(
        'res.company',
        string='Company / Branch',
        default=lambda self: self.env.company,
    )
    all_companies = fields.Boolean(string='All Companies', default=False)
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

    def _fmt(self, val):
        return '{:,.2f}'.format(val or 0.0)

    def _get_lines(self, account_types, company_ids):
        domain = [
            ('move_id.state', '=', 'posted'),
            ('move_id.date', '>=', self.date_from),
            ('move_id.date', '<=', self.date_to),
            ('account_id.account_type', 'in', account_types),
        ]
        if company_ids:
            domain.append(('company_id', 'in', company_ids))

        groups = self.env['account.move.line'].read_group(
            domain,
            fields=['account_id', 'balance'],
            groupby=['account_id'],
        )
        result = []
        for g in groups:
            account = self.env['account.account'].browse(g['account_id'][0])
            result.append({
                'name': account.name,
                'code': account.code,
                'balance': g['balance'],
            })
        return result

    def _build_data(self):
        if self.all_companies:
            company_ids = self.env['res.company'].search([]).ids
            company = self.env.company
        else:
            company_ids = [self.company_id.id] if self.company_id else []
            company = self.company_id or self.env.company

        # ── Revenue ──────────────────────────────────────────────
        # income accounts: credit = positive revenue → negate balance
        sales_lines = self._get_lines(['income'], company_ids)
        sales_total = sum(-l['balance'] for l in sales_lines)

        sales_return_lines = self._get_lines(['income_other'], company_ids)
        sales_return_total = sum(-l['balance'] for l in sales_return_lines)

        total_revenue = sales_total - sales_return_total

        # ── Cost of Sales ────────────────────────────────────────
        # expense_direct_cost: debit = positive cost → keep balance positive
        cogs_lines = self._get_lines(['expense_direct_cost'], company_ids)
        cogs_total = sum(l['balance'] for l in cogs_lines)

        total_cost_of_sales = cogs_total
        gross_profit = total_revenue - total_cost_of_sales

        # ── Other Income & Expenses ──────────────────────────────
        other_expense_lines = self._get_lines(
            ['expense', 'expense_depreciation'], company_ids
        )
        other_expense_total = sum(l['balance'] for l in other_expense_lines)

        other_income_lines = self._get_lines([], company_ids)  # placeholder
        other_income_total = 0.0

        total_other = other_expense_total - other_income_total
        net_profit = gross_profit - total_other

        # Build display lines with formatted balances
        def fmt_lines_expense(lines):
            return [{'name': l['name'], 'code': l['code'],
                     'balance': self._fmt(l['balance'])} for l in lines]

        def fmt_lines_income(lines):
            return [{'name': l['name'], 'code': l['code'],
                     'balance': self._fmt(-l['balance'])} for l in lines]

        return {
            # Company info
            'company_name': company.name or '',
            'company_name_ar': company.partner_id.name or '',
            'vat': company.vat or '',
            'street': company.street or '',
            'city': company.city or '',
            'zip': company.zip or '',
            'date_from': str(self.date_from),
            'date_to': str(self.date_to),

            # Revenue
            'sales_lines': fmt_lines_income(sales_lines),
            'sales_total': self._fmt(sales_total),
            'sales_return_lines': fmt_lines_income(sales_return_lines),
            'sales_return_total': self._fmt(sales_return_total),
            'total_revenue': self._fmt(total_revenue),

            # Cost of Sales
            'cogs_lines': fmt_lines_expense(cogs_lines),
            'cogs_total': self._fmt(cogs_total),
            'total_cost_of_sales': self._fmt(-total_cost_of_sales),

            # Gross Profit
            'gross_profit': self._fmt(gross_profit),

            # Other Income & Expenses
            'other_expense_lines': fmt_lines_expense(other_expense_lines),
            'other_expense_total': self._fmt(other_expense_total),
            'total_other': self._fmt(-total_other),

            # Net Profit
            'net_profit': self._fmt(net_profit),
        }

    def action_show_report(self):
        data = self._build_data()
        return self.env.ref(
            'income_statement_report.action_income_statement_report'
        ).report_action(self, data={'form': data})

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


class IncomeStatementReport(models.AbstractModel):
    """
    AbstractModel required by Odoo's report engine.
    The _name must match: report.<report_action_model>
    This lets us use _get_report_values to inject data correctly.
    """
    _name = 'report.income_statement_report.report_income_statement_template'
    _description = 'Income Statement Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        form = data.get('form', {}) if data else {}
        docs = self.env['income.statement.wizard'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'income.statement.wizard',
            'docs': docs,
            'form': form,
        }